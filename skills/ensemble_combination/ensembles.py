"""Seven CIO ensemble combination methods (Section 3.6)."""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd


def simple_average(weights: Dict[str, np.ndarray]) -> np.ndarray:
    W = np.vstack(list(weights.values()))
    return W.mean(axis=0)


def inverse_tracking_error(weights: Dict[str, np.ndarray], Sigma: np.ndarray) -> np.ndarray:
    """Weight each PC inversely to its TE vs the centroid."""
    W = np.vstack(list(weights.values()))
    centroid = W.mean(axis=0)
    tes = np.array([np.sqrt(max((W[i] - centroid) @ Sigma @ (W[i] - centroid), 1e-12))
                    for i in range(W.shape[0])])
    inv = 1.0 / np.maximum(tes, 1e-9)
    inv = inv / inv.sum()
    out = inv @ W
    return out


def backtest_sharpe_weighted(weights: Dict[str, np.ndarray], sharpes: Dict[str, float]) -> np.ndarray:
    keys = list(weights.keys())
    s = np.array([max(0.01, sharpes.get(k, 0.0)) for k in keys])
    s = s / s.sum()
    W = np.vstack([weights[k] for k in keys])
    return s @ W


def meta_optimization(weights: Dict[str, np.ndarray], Sigma: np.ndarray, returns: pd.DataFrame) -> np.ndarray:
    """Treat each PC's portfolio as a synthetic 'asset' and pick min-variance combo."""
    keys = list(weights.keys())
    W = np.vstack([weights[k] for k in keys])     # K x N
    # Synthetic asset returns
    synth = (returns.values @ W.T)               # T x K
    Sigma_k = np.cov(synth.T) + 1e-6 * np.eye(len(keys))
    inv = np.linalg.solve(Sigma_k, np.ones(len(keys)))
    inv = np.maximum(inv, 0)
    if inv.sum() <= 0:
        inv = np.ones(len(keys))
    inv = inv / inv.sum()
    return inv @ W


def regime_conditional(weights: Dict[str, np.ndarray], regime: str) -> np.ndarray:
    """Pre-tabulated method emphasis by regime."""
    table = {
        "expansion":  {"max_sharpe": 1.5, "black_litterman": 1.3, "tpa_two_factor": 1.2,
                       "equal_weight": 1.0},
        "late-cycle": {"max_diversification": 1.5, "risk_parity": 1.4, "hrp": 1.3,
                       "tail_risk_parity": 1.3, "max_entropy": 1.2, "black_litterman": 1.1},
        "recession":  {"gmv": 1.5, "risk_parity": 1.4, "cvar_min": 1.3, "tail_risk_parity": 1.3},
        "recovery":   {"max_sharpe": 1.4, "mean_downside": 1.2, "resampled_ef": 1.3,
                       "equal_weight": 1.0},
    }
    weights_method = table.get(regime, {})
    keys = list(weights.keys())
    base = np.array([weights_method.get(k.replace("-", "_"), 1.0) for k in keys])
    base = base / base.sum()
    W = np.vstack([weights[k] for k in keys])
    return base @ W


def composite_score_weighted(weights: Dict[str, np.ndarray], scores: Dict[str, float]) -> np.ndarray:
    keys = list(weights.keys())
    s = np.array([max(0.01, scores.get(k, 0.0)) for k in keys])
    s = s / s.sum()
    W = np.vstack([weights[k] for k in keys])
    return s @ W


def trimmed_mean(weights: Dict[str, np.ndarray], scores: Dict[str, float], trim: float = 0.1) -> np.ndarray:
    keys = list(weights.keys())
    n = len(keys)
    if n < 4:
        return simple_average(weights)
    cut = max(1, int(trim * n))
    ordered = sorted(keys, key=lambda k: scores.get(k, 0.0))
    keep = ordered[cut:n - cut] or ordered
    W = np.vstack([weights[k] for k in keep])
    return W.mean(axis=0)


METHODS = {
    "simple_average":     simple_average,
    "inverse_te":         inverse_tracking_error,
    "backtest_sharpe":    backtest_sharpe_weighted,
    "meta_optimization":  meta_optimization,
    "regime_conditional": regime_conditional,
    "composite_score":    composite_score_weighted,
    "trimmed_mean":       trimmed_mean,
}
