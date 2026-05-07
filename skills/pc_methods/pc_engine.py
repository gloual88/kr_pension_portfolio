"""
Portfolio Construction (PC) engine.

All 21 portfolio construction methods from Exhibit 5 of Ang, Azimbayev, Kim (2026)
plus the PC-Researcher's maximum-entropy proposal.

Each method takes (mu, Sigma, returns_panel, constraints) and returns a numpy
weight vector that sums to 1.0 and (where possible) respects category and
position bounds. We use lightweight numerical solvers from scipy where helpful;
methods that would normally require a CVX solver use sensible heuristic
projections so the pipeline can run without external optimizers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
@dataclass
class Constraints:
    n: int
    categories: List[str]
    min_w: np.ndarray                            # per asset
    max_w: np.ndarray
    cat_min: Dict[str, float] = field(default_factory=dict)
    cat_max: Dict[str, float] = field(default_factory=dict)


def _project_to_constraints(w: np.ndarray, cons: Constraints, max_iter: int = 200, tol: float = 1e-8) -> np.ndarray:
    """Iterative projection: clip to box, enforce category bounds, renormalize."""
    n = cons.n
    w = np.clip(w, cons.min_w, cons.max_w)
    s = w.sum()
    if s <= 0:
        w = np.ones(n) / n
        return w
    w = w / s

    for _ in range(max_iter):
        prev = w.copy()
        # Box first
        w = np.clip(w, cons.min_w, cons.max_w)
        # Renormalise
        s = w.sum()
        if s <= 0:
            w = np.ones(n) / n
            return w
        w = w / s

        # Category bounds
        for cat, mn in cons.cat_min.items():
            mask = np.array([c == cat for c in cons.categories])
            cur = w[mask].sum()
            if cur < mn - tol and mask.sum() > 0:
                deficit = mn - cur
                add = deficit / mask.sum()
                w[mask] = w[mask] + add
                w = np.clip(w, cons.min_w, cons.max_w)
                w = w / w.sum()
        for cat, mx in cons.cat_max.items():
            mask = np.array([c == cat for c in cons.categories])
            cur = w[mask].sum()
            if cur > mx + tol and mask.sum() > 0:
                excess = cur - mx
                cut = excess / mask.sum()
                w[mask] = np.maximum(0.0, w[mask] - cut)
                w = np.clip(w, cons.min_w, cons.max_w)
                if w.sum() > 0:
                    w = w / w.sum()
        if np.max(np.abs(w - prev)) < tol:
            break

    # Final clip + renormalize
    w = np.clip(w, cons.min_w, cons.max_w)
    if w.sum() <= 0:
        return np.ones(n) / n
    return w / w.sum()


# ---------------------------------------------------------------------------
# A. Heuristic
# ---------------------------------------------------------------------------
def equal_weight(mu, Sigma, panel, cons):
    return _project_to_constraints(np.ones(cons.n) / cons.n, cons)


def market_cap_weight(mu, Sigma, panel, cons):
    # Synthetic cap weight: use a fixed prior tilted to large equities.
    base = np.ones(cons.n)
    # Rough cap-weight prior: heavier on US LC, intl developed, intermediate UST
    priors = {
        "us-large-cap": 4.0, "us-growth": 1.6, "us-value": 1.4, "us-small-cap": 0.6,
        "intl-developed": 1.6, "emerging-markets": 0.8,
        "short-treasuries": 1.0, "intermediate-treasuries": 1.6, "long-treasuries": 1.0,
        "ig-corporates": 1.2, "hy-corporates": 0.5, "intl-sovereigns": 0.8,
        "intl-corporates": 0.5, "usd-em-debt": 0.4,
        "reits": 0.4, "gold": 0.3, "commodities": 0.4, "cash": 0.5,
    }
    if hasattr(panel, "columns"):
        w = np.array([priors.get(c, 1.0) for c in panel.columns])
    else:
        w = base
    return _project_to_constraints(w / w.sum(), cons)


def inverse_volatility(mu, Sigma, panel, cons):
    vol = np.sqrt(np.diag(Sigma))
    vol = np.where(vol > 1e-8, vol, 1e-8)
    w = 1.0 / vol
    w = w / w.sum()
    return _project_to_constraints(w, cons)


def inverse_variance(mu, Sigma, panel, cons):
    var = np.diag(Sigma)
    var = np.where(var > 1e-10, var, 1e-10)
    w = 1.0 / var
    w = w / w.sum()
    return _project_to_constraints(w, cons)


def volatility_targeting(mu, Sigma, panel, cons, target_vol: float = 0.10):
    # Inverse-vol with leverage capped at 1.0 (long-only).
    base = inverse_volatility(mu, Sigma, panel, cons)
    return base


# ---------------------------------------------------------------------------
# B. Return-optimized
# ---------------------------------------------------------------------------
def _projected_grad(mu, Sigma, cons, lam=10.0, iters=500, lr=0.02):
    n = cons.n
    w = np.ones(n) / n
    for _ in range(iters):
        grad = -mu + lam * Sigma @ w
        w = w - lr * grad
        w = _project_to_constraints(w, cons)
    return w


def max_sharpe(mu, Sigma, panel, cons):
    n = cons.n
    rf = 0.0  # mu already in excess of rf if caller wants

    def neg_sharpe(w):
        ret = w @ mu
        vol = np.sqrt(max(w @ Sigma @ w, 1e-12))
        return -(ret - rf) / vol

    bounds = list(zip(cons.min_w, cons.max_w))
    cons_eq = ({"type": "eq", "fun": lambda w: w.sum() - 1.0},)
    x0 = np.ones(n) / n
    res = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=cons_eq,
                   options={"maxiter": 200, "ftol": 1e-9})
    if res.success:
        return _project_to_constraints(res.x, cons)
    return _projected_grad(mu, Sigma, cons)


def black_litterman(mu, Sigma, panel, cons):
    """BL with weak views: anchor to equilibrium, blend with mu."""
    # Treat the inverse-vol portfolio as 'market'; reverse-optimize to get pi.
    iv = inverse_volatility(mu, Sigma, panel, cons)
    lam = 2.5
    pi = lam * Sigma @ iv
    tau = 0.05
    P = np.eye(cons.n)
    Q = mu
    Omega = np.diag(np.diag(P @ Sigma @ P.T)) * (1.0 / max(0.5, 1.0))
    M_inv = np.linalg.inv(np.linalg.inv(tau * Sigma) + P.T @ np.linalg.inv(Omega + 1e-8 * np.eye(cons.n)) @ P)
    bl_mu = M_inv @ (np.linalg.inv(tau * Sigma) @ pi + P.T @ np.linalg.inv(Omega + 1e-8 * np.eye(cons.n)) @ Q)
    return _projected_grad(bl_mu, Sigma, cons, lam=lam)


def robust_mv(mu, Sigma, panel, cons, kappa: float = 0.05):
    """Goldfarb-Iyengar style: shrink mu by kappa·sqrt(diag Sigma)."""
    shrink = kappa * np.sqrt(np.diag(Sigma))
    mu_robust = mu - shrink
    return _projected_grad(mu_robust, Sigma, cons, lam=8.0)


def resampled_ef(mu, Sigma, panel, cons, B: int = 50, seed: int = 11):
    rng = np.random.default_rng(seed)
    n = cons.n
    L = np.linalg.cholesky(Sigma + 1e-8 * np.eye(n))
    accum = np.zeros(n)
    for _ in range(B):
        eps = rng.standard_normal(n)
        mu_b = mu + L @ eps * 0.20
        accum = accum + max_sharpe(mu_b, Sigma, panel, cons)
    return _project_to_constraints(accum / B, cons)


def mean_downside(mu, Sigma, panel, cons):
    """Sortino-like: penalize downside variance only."""
    n = cons.n
    if isinstance(panel, pd.DataFrame):
        clean = panel.dropna(how="any")
        if clean.shape[0] < 60:
            # Insufficient overlap — fall back to using prior Sigma directly.
            return _projected_grad(mu, Sigma + 1e-6 * np.eye(n), cons, lam=8.0)
        rets = clean.values
    else:
        rets = np.asarray(panel)
    downside = np.minimum(rets, 0.0)
    Sigma_d = np.cov(downside.T) * 252.0
    if not np.all(np.isfinite(Sigma_d)):
        return _projected_grad(mu, Sigma + 1e-6 * np.eye(n), cons, lam=8.0)
    return _projected_grad(mu, Sigma_d + 1e-6 * np.eye(n), cons, lam=8.0)


# ---------------------------------------------------------------------------
# C. Risk-structured
# ---------------------------------------------------------------------------
def gmv(mu, Sigma, panel, cons):
    n = cons.n

    def port_var(w):
        return w @ Sigma @ w

    bounds = list(zip(cons.min_w, cons.max_w))
    cons_eq = ({"type": "eq", "fun": lambda w: w.sum() - 1.0},)
    res = minimize(port_var, np.ones(n) / n, method="SLSQP",
                   bounds=bounds, constraints=cons_eq,
                   options={"maxiter": 200})
    if res.success:
        return _project_to_constraints(res.x, cons)
    return inverse_variance(mu, Sigma, panel, cons)


def risk_parity(mu, Sigma, panel, cons, iters: int = 500):
    """Cyclical-coordinate descent for ERC (Maillard et al. 2010)."""
    n = cons.n
    w = np.ones(n) / n
    for _ in range(iters):
        grad = Sigma @ w
        rc = w * grad
        target = rc.mean()
        # Update step: w_i ← w_i * (target / rc_i)^0.5
        ratio = np.where(rc > 1e-12, np.sqrt(target / np.maximum(rc, 1e-12)), 1.0)
        w = w * ratio
        w = w / w.sum()
        w = _project_to_constraints(w, cons)
    return w


def hierarchical_risk_parity(mu, Sigma, panel, cons):
    """López de Prado HRP: cluster on correlation distance, recursive bisection."""
    n = cons.n
    vol = np.sqrt(np.diag(Sigma))
    corr = Sigma / np.outer(vol, vol)
    np.fill_diagonal(corr, 1.0)
    dist = np.sqrt(0.5 * (1.0 - corr))
    # Single-linkage clustering
    order = _quasi_diag(_single_linkage(dist))
    w = _hrp_alloc(Sigma, order)
    return _project_to_constraints(w, cons)


def max_diversification(mu, Sigma, panel, cons):
    """Choueifaty-Coignard: maximize (w'σ) / sqrt(w'Σw)."""
    n = cons.n
    vol = np.sqrt(np.diag(Sigma))

    def neg_div(w):
        wvol = w @ vol
        port = np.sqrt(max(w @ Sigma @ w, 1e-12))
        return -(wvol / port)

    bounds = list(zip(cons.min_w, cons.max_w))
    cons_eq = ({"type": "eq", "fun": lambda w: w.sum() - 1.0},)
    res = minimize(neg_div, np.ones(n) / n, method="SLSQP",
                   bounds=bounds, constraints=cons_eq,
                   options={"maxiter": 300})
    if res.success:
        return _project_to_constraints(res.x, cons)
    return inverse_volatility(mu, Sigma, panel, cons)


def min_correlation(mu, Sigma, panel, cons):
    """Varadi et al.: weight inversely to mean off-diagonal correlation."""
    vol = np.sqrt(np.diag(Sigma))
    corr = Sigma / np.outer(vol, vol)
    np.fill_diagonal(corr, 0.0)
    avg_corr = corr.mean(axis=1)
    rank = np.argsort(np.argsort(avg_corr))
    inv = (rank.max() - rank + 1).astype(float)
    inv_vol = 1.0 / np.maximum(vol, 1e-8)
    w = inv * inv_vol
    w = w / w.sum()
    return _project_to_constraints(w, cons)


# ---------------------------------------------------------------------------
# D. Non-traditional
# ---------------------------------------------------------------------------
def cvar_min(mu, Sigma, panel, cons, alpha: float = 0.95, samples: int = 1000, seed: int = 19):
    """Approximate CVaR-min: minimize expected shortfall at alpha via gradient on simulated tails."""
    n = cons.n
    if isinstance(panel, pd.DataFrame):
        rets = panel.values
    else:
        rets = np.asarray(panel)
    if rets.shape[0] > samples:
        rng = np.random.default_rng(seed)
        idx = rng.choice(rets.shape[0], samples, replace=False)
        rets = rets[idx]
    n_obs = rets.shape[0]

    def neg_cvar(w):
        port = rets @ w
        cutoff = np.quantile(port, 1.0 - alpha)
        tail = port[port <= cutoff]
        if tail.size == 0:
            return 0.0
        return -float(tail.mean())   # we minimize the *negative* tail mean (i.e. shortfall)

    bounds = list(zip(cons.min_w, cons.max_w))
    cons_eq = ({"type": "eq", "fun": lambda w: w.sum() - 1.0},)
    res = minimize(neg_cvar, np.ones(n) / n, method="SLSQP",
                   bounds=bounds, constraints=cons_eq,
                   options={"maxiter": 200})
    if res.success:
        return _project_to_constraints(res.x, cons)
    return gmv(mu, Sigma, panel, cons)


def max_dd_constrained(mu, Sigma, panel, cons, dd_limit: float = 0.25):
    """Heuristic: blend mean-variance with extra penalty on assets with worst trailing DD."""
    n = cons.n
    if isinstance(panel, pd.DataFrame):
        cum = (1 + panel).cumprod()
        peak = cum.cummax()
        dd = (cum / peak - 1.0).min().values
    else:
        dd = np.zeros(n)
    penalty = np.maximum(0.0, -dd - dd_limit) * 5.0  # extra penalty above limit
    mu_adj = mu - penalty
    return _projected_grad(mu_adj, Sigma, cons, lam=8.0)


def tail_risk_parity(mu, Sigma, panel, cons, alpha: float = 0.95, seed: int = 23):
    """Risk parity but on tail contributions (downside semi-cov)."""
    if isinstance(panel, pd.DataFrame):
        rets = panel.values
    else:
        rets = np.asarray(panel)
    n = cons.n
    threshold = np.quantile(rets, 1.0 - alpha, axis=0)
    tail = np.where(rets <= threshold, rets, 0.0)
    Sigma_tail = np.cov(tail.T) * 252.0
    Sigma_tail = Sigma_tail + 1e-6 * np.eye(n)
    return risk_parity(mu, Sigma_tail, panel, cons)


def tpa_two_factor(mu, Sigma, panel, cons):
    """Total Portfolio Allocation 2-factor: equity vs bond factor exposures."""
    n = cons.n
    if isinstance(panel, pd.DataFrame):
        cols = list(panel.columns)
    else:
        cols = [f"a{i}" for i in range(n)]

    # Map slugs to (equity beta, bond beta) loadings (simple priors).
    loadings = {
        "us-large-cap": (1.00, -0.10), "us-small-cap": (1.15, -0.10),
        "us-value": (0.95, -0.05), "us-growth": (1.10, -0.15),
        "intl-developed": (0.90, -0.05), "emerging-markets": (1.10, -0.10),
        "short-treasuries": (-0.02, 0.20), "intermediate-treasuries": (-0.10, 0.65),
        "long-treasuries": (-0.20, 1.10), "ig-corporates": (0.20, 0.65),
        "hy-corporates": (0.55, 0.20), "intl-sovereigns": (-0.05, 0.55),
        "intl-corporates": (0.20, 0.55), "usd-em-debt": (0.40, 0.45),
        "reits": (0.85, -0.05), "gold": (0.05, 0.10),
        "commodities": (0.30, -0.10), "cash": (0.00, 0.05),
    }
    L = np.array([loadings.get(c, (0.5, 0.3)) for c in cols])
    # Solve for weights minimizing distance to factor target (60% eq, 40% bond).
    target = np.array([0.55, 0.45])

    def loss(w):
        f = w @ L
        return float(np.sum((f - target) ** 2)) + 0.5 * float(w @ Sigma @ w)

    bounds = list(zip(cons.min_w, cons.max_w))
    cons_eq = ({"type": "eq", "fun": lambda w: w.sum() - 1.0},)
    res = minimize(loss, np.ones(n) / n, method="SLSQP",
                   bounds=bounds, constraints=cons_eq,
                   options={"maxiter": 200})
    if res.success:
        return _project_to_constraints(res.x, cons)
    return equal_weight(mu, Sigma, panel, cons)


def adversarial_diversifier(mu, Sigma, panel, cons, others: List[np.ndarray],
                             sharpe_floor_frac: float = 0.75):
    """
    Maximizes tracking variance vs the centroid of `others`, subject to a Sharpe-ratio
    floor of `sharpe_floor_frac` × max-Sharpe Sharpe.
    """
    if not others:
        return equal_weight(mu, Sigma, panel, cons)

    centroid = np.mean(np.vstack(others), axis=0)
    n = cons.n

    # Compute reference max-Sharpe Sharpe.
    w_ms = max_sharpe(mu, Sigma, panel, cons)
    s_max = (w_ms @ mu) / max(np.sqrt(w_ms @ Sigma @ w_ms), 1e-9)
    floor = sharpe_floor_frac * s_max

    def neg_te(w):
        d = w - centroid
        return -float(d @ Sigma @ d)

    def sharpe_constraint(w):
        ret = w @ mu
        vol = np.sqrt(max(w @ Sigma @ w, 1e-12))
        return ret / vol - floor

    bounds = list(zip(cons.min_w, cons.max_w))
    cons_list = [
        {"type": "eq", "fun": lambda w: w.sum() - 1.0},
        {"type": "ineq", "fun": sharpe_constraint},
    ]
    res = minimize(neg_te, np.ones(n) / n, method="SLSQP",
                   bounds=bounds, constraints=cons_list,
                   options={"maxiter": 300})
    if res.success:
        return _project_to_constraints(res.x, cons)
    # Fallback: pull away from centroid.
    pull = np.where(centroid > 1.0 / n, cons.min_w, cons.max_w)
    return _project_to_constraints(pull, cons)


# ---------------------------------------------------------------------------
# E. Researcher: Maximum Entropy (Bera-Park 2008)
# ---------------------------------------------------------------------------
def max_entropy(mu, Sigma, panel, cons, sharpe_floor: float = 0.30):
    """
    Maximize Shannon entropy -Σ w·ln w subject to a Sharpe floor.
    """
    n = cons.n

    def neg_ent(w):
        x = np.clip(w, 1e-8, 1.0)
        return float(np.sum(x * np.log(x)))

    def sharpe_floor_c(w):
        ret = w @ mu
        vol = np.sqrt(max(w @ Sigma @ w, 1e-12))
        return ret / vol - sharpe_floor

    bounds = list(zip(np.maximum(cons.min_w, 1e-4), cons.max_w))
    cons_list = [
        {"type": "eq", "fun": lambda w: w.sum() - 1.0},
        {"type": "ineq", "fun": sharpe_floor_c},
    ]
    res = minimize(neg_ent, np.ones(n) / n, method="SLSQP",
                   bounds=bounds, constraints=cons_list,
                   options={"maxiter": 300})
    if res.success:
        return _project_to_constraints(res.x, cons)
    return equal_weight(mu, Sigma, panel, cons)


# ---------------------------------------------------------------------------
# HRP helpers
# ---------------------------------------------------------------------------
def _single_linkage(D: np.ndarray) -> List[Tuple[int, int, float, int]]:
    n = D.shape[0]
    clusters = {i: [i] for i in range(n)}
    Z: List[Tuple[int, int, float, int]] = []
    cur = D.copy().astype(float)
    np.fill_diagonal(cur, np.inf)
    next_id = n
    active = list(range(n))
    while len(active) > 1:
        i_idx, j_idx = np.unravel_index(np.argmin(cur), cur.shape)
        # Pick canonical pair.
        if i_idx > j_idx:
            i_idx, j_idx = j_idx, i_idx
        d = cur[i_idx, j_idx]
        a_i, a_j = active[i_idx], active[j_idx]
        new_size = len(clusters[a_i]) + len(clusters[a_j])
        Z.append((a_i, a_j, float(d), new_size))
        # Merge
        new_cluster = clusters[a_i] + clusters[a_j]
        clusters[next_id] = new_cluster
        # Update distance matrix: replace row i with min, drop row j.
        new_row = np.minimum(cur[i_idx, :], cur[j_idx, :])
        cur[i_idx, :] = new_row
        cur[:, i_idx] = new_row
        cur[i_idx, i_idx] = np.inf
        cur = np.delete(cur, j_idx, axis=0)
        cur = np.delete(cur, j_idx, axis=1)
        active[i_idx] = next_id
        active.pop(j_idx)
        next_id += 1
    return Z


def _quasi_diag(Z: List[Tuple[int, int, float, int]]) -> List[int]:
    """Recursively expand the linkage tree into leaf order."""
    if not Z:
        return [0]
    n = len(Z) + 1
    last = Z[-1]
    res = [last[0], last[1]]
    expanded = True
    while expanded:
        expanded = False
        new = []
        for x in res:
            if x < n:
                new.append(x)
            else:
                a, b, _, _ = Z[x - n]
                new.extend([a, b])
                expanded = True
        res = new
    return res


def _hrp_alloc(Sigma: np.ndarray, order: List[int]) -> np.ndarray:
    n = Sigma.shape[0]
    w = np.ones(n)
    cur = [order]
    while cur:
        new = []
        for cluster in cur:
            if len(cluster) <= 1:
                continue
            mid = len(cluster) // 2
            left = cluster[:mid]
            right = cluster[mid:]
            v_left = _ivp_var(Sigma, left)
            v_right = _ivp_var(Sigma, right)
            alpha = 1.0 - v_left / (v_left + v_right + 1e-12)
            w[left] = w[left] * alpha
            w[right] = w[right] * (1.0 - alpha)
            new.append(left)
            new.append(right)
        cur = new
    return w / w.sum()


def _ivp_var(Sigma: np.ndarray, idx: List[int]) -> float:
    sub = Sigma[np.ix_(idx, idx)]
    iv = 1.0 / np.diag(sub)
    iv = iv / iv.sum()
    return float(iv @ sub @ iv)


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
DISPATCH: Dict[str, Callable] = {
    "equal_weight":           equal_weight,
    "market_cap_weight":      market_cap_weight,
    "inverse_volatility":     inverse_volatility,
    "inverse_variance":       inverse_variance,
    "volatility_targeting":   volatility_targeting,
    "max_sharpe":             max_sharpe,
    "black_litterman":        black_litterman,
    "robust_mv":              robust_mv,
    "resampled_ef":           resampled_ef,
    "mean_downside":          mean_downside,
    "gmv":                    gmv,
    "risk_parity":            risk_parity,
    "hrp":                    hierarchical_risk_parity,
    "max_diversification":    max_diversification,
    "min_correlation":        min_correlation,
    "cvar_min":               cvar_min,
    "max_dd_constrained":     max_dd_constrained,
    "tail_risk_parity":       tail_risk_parity,
    "tpa_two_factor":         tpa_two_factor,
    "max_entropy":            max_entropy,
    # 'adversarial_diversifier' is handled separately because it depends on others.
}


def make_constraints(
    asset_classes: List[dict],
    pos_min: float = 0.0,
    pos_max: float = 0.30,
    cat_min: Optional[Dict[str, float]] = None,
    cat_max: Optional[Dict[str, float]] = None,
) -> Constraints:
    n = len(asset_classes)
    return Constraints(
        n=n,
        categories=[ac["category"] for ac in asset_classes],
        min_w=np.full(n, pos_min),
        max_w=np.full(n, pos_max),
        cat_min=cat_min or {},
        cat_max=cat_max or {},
    )
