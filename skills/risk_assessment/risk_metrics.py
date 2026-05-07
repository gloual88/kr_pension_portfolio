"""Risk metrics and IPS compliance checks (CRO skill)."""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd


def ex_ante_vol(w: np.ndarray, Sigma: np.ndarray) -> float:
    return float(np.sqrt(max(w @ Sigma @ w, 0.0)))


def ex_ante_var(w: np.ndarray, mu: np.ndarray, Sigma: np.ndarray, alpha: float = 0.95) -> float:
    """Parametric Gaussian VaR over 1Y horizon."""
    z = 1.645 if alpha == 0.95 else 2.326
    mean = float(w @ mu)
    vol = ex_ante_vol(w, Sigma)
    return float(mean - z * vol)


def backtest_metrics(w: np.ndarray, returns: pd.DataFrame) -> Dict[str, float]:
    if returns is None or returns.empty:
        return {"backtest_sharpe": 0.0, "backtest_vol": 0.0, "backtest_maxdd": 0.0}
    port = (returns.values @ w)
    port_s = pd.Series(port, index=returns.index)
    ann = 252
    mean_ann = float(port_s.mean() * ann)
    vol_ann = float(port_s.std(ddof=0) * np.sqrt(ann))
    sharpe = mean_ann / vol_ann if vol_ann > 0 else 0.0
    cum = (1 + port_s).cumprod()
    peak = cum.cummax()
    dd = float((cum / peak - 1.0).min())
    return {"backtest_sharpe": sharpe, "backtest_vol": vol_ann, "backtest_maxdd": dd}


def concentration_metrics(w: np.ndarray) -> Dict[str, float]:
    w_pos = np.clip(w, 1e-12, None)
    hhi = float(np.sum(w_pos ** 2))
    eff_n = float(1.0 / hhi) if hhi > 0 else 0.0
    top3 = float(np.sort(w)[-3:].sum())
    return {"hhi": hhi, "effective_n": eff_n, "top3": top3}


def category_weights(w: np.ndarray, asset_classes: List[dict]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for i, ac in enumerate(asset_classes):
        out[ac["category"]] = out.get(ac["category"], 0.0) + float(w[i])
    return out


def ips_compliance(
    w: np.ndarray,
    asset_classes: List[dict],
    Sigma: np.ndarray,
    benchmark_w: Optional[np.ndarray],
    ips: dict,
) -> Dict[str, object]:
    flags: List[str] = []

    # Position limits
    pos = ips.get("constraints", {}).get("position_limits", {})
    p_min, p_max = pos.get("min", 0.0), pos.get("max", 1.0)
    for i, ac in enumerate(asset_classes):
        if w[i] < p_min - 1e-6 or w[i] > p_max + 1e-6:
            flags.append(f"position[{ac['slug']}]={w[i]:.3f} outside [{p_min},{p_max}]")

    # Category bounds
    cats = category_weights(w, asset_classes)
    cat_b = ips.get("constraints", {}).get("category_bounds", {})
    for cat, b in cat_b.items():
        cw = cats.get(cat, 0.0)
        if cw < b.get("min", 0.0) - 1e-6 or cw > b.get("max", 1.0) + 1e-6:
            flags.append(f"category[{cat}]={cw:.2%} outside [{b['min']:.2%},{b['max']:.2%}]")

    # Expected vol band
    vol = ex_ante_vol(w, Sigma)
    band = ips.get("objective", {}).get("expected_volatility_band", {})
    lo, hi = band.get("low", 0.0), band.get("high", 1.0)
    if vol < lo - 1e-6 or vol > hi + 1e-6:
        flags.append(f"vol={vol:.2%} outside [{lo:.2%},{hi:.2%}]")

    # Tracking error vs benchmark
    te_value = None
    if benchmark_w is not None:
        d = w - benchmark_w
        te = float(np.sqrt(max(d @ Sigma @ d, 0.0)))
        te_value = te
        bgt = ips.get("active_risk_budget", {}).get("max_tracking_error", 1.0)
        if te > bgt + 1e-6:
            flags.append(f"tracking_error={te:.2%} exceeds budget {bgt:.2%}")

    return {
        "compliance_score": float(1.0 if not flags else max(0.0, 1.0 - 0.10 * len(flags))),
        "flags": flags,
        "ex_ante_vol": vol,
        "tracking_error": te_value,
        "category_weights": cats,
    }


def factor_tilts(w: np.ndarray, asset_classes: List[dict]) -> Dict[str, float]:
    """Crude factor tilts from sensitivities in IPS."""
    keys = ["growth", "rates", "inflation", "dollar"]
    tilts = {k: 0.0 for k in keys}
    for i, ac in enumerate(asset_classes):
        sens = ac.get("macro_sensitivity", {})
        for k in keys:
            tilts[k] += float(w[i]) * float(sens.get(k, 0))
    return tilts


def cma_utilization(w: np.ndarray, mu: np.ndarray) -> float:
    """How much of the portfolio Sharpe contribution comes from CMAs vs equal weight?"""
    eq = np.ones_like(w) / len(w)
    base = float(eq @ mu)
    diff = float(w @ mu) - base
    # Normalize to [-1, 1]
    if abs(base) < 1e-9:
        return 0.0
    return float(np.tanh(2.0 * diff / max(abs(base), 1e-9)))


def diversification_score(w: np.ndarray, Sigma: np.ndarray) -> float:
    """Choueifaty-Coignard ratio normalized."""
    vol = np.sqrt(np.diag(Sigma))
    wvol = float(w @ vol)
    port = ex_ante_vol(w, Sigma)
    if port <= 1e-9:
        return 0.0
    ratio = wvol / port
    # Map [1, sqrt(N)] -> [0, 1]
    n = len(w)
    cap = float(np.sqrt(n))
    return float(min(1.0, max(0.0, (ratio - 1.0) / (cap - 1.0))))


def estimation_robustness(method: str, regime: str) -> float:
    """Heuristic regime/method robustness score in [0, 1]."""
    base = {
        "equal_weight": 0.85, "market_cap_weight": 0.55,
        "inverse_volatility": 0.80, "inverse_variance": 0.78, "volatility_targeting": 0.70,
        "max_sharpe": 0.45, "black_litterman": 0.65, "robust_mv": 0.70,
        "resampled_ef": 0.65, "mean_downside": 0.55,
        "gmv": 0.65, "risk_parity": 0.80, "hrp": 0.75,
        "max_diversification": 0.70, "min_correlation": 0.65,
        "cvar_min": 0.55, "max_dd_constrained": 0.55,
        "tail_risk_parity": 0.65, "tpa_two_factor": 0.65,
        "adversarial_diversifier": 0.30, "max_entropy": 0.75,
    }.get(method, 0.5)
    if regime in ("late-cycle", "recession"):
        # Risk-structured methods preferred
        if method in ("risk_parity", "hrp", "max_diversification", "gmv"):
            base += 0.05
        if method in ("max_sharpe", "mean_downside"):
            base -= 0.05
    return float(min(1.0, max(0.0, base)))


def regime_fit(method: str, regime: str) -> float:
    table = {
        "expansion":  {"max_sharpe": 0.85, "black_litterman": 0.80, "tpa_two_factor": 0.75,
                       "equal_weight": 0.70, "market_cap_weight": 0.70},
        "late-cycle": {"max_diversification": 0.90, "risk_parity": 0.85, "hrp": 0.80,
                       "black_litterman": 0.75, "tail_risk_parity": 0.80, "max_entropy": 0.65},
        "recession":  {"gmv": 0.85, "risk_parity": 0.85, "tail_risk_parity": 0.80,
                       "max_diversification": 0.75, "cvar_min": 0.75},
        "recovery":   {"max_sharpe": 0.80, "mean_downside": 0.75, "resampled_ef": 0.80,
                       "tpa_two_factor": 0.70, "equal_weight": 0.65},
    }
    fit = table.get(regime, {}).get(method, 0.50)
    return float(fit)
