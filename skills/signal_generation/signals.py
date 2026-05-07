"""Signal generation for asset-class agents."""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def macro_signal(macro_scores: Dict[str, float], sensitivity: Dict[str, int]) -> float:
    """Dot product of regime scores and asset-class sensitivities (clipped to [-1,1])."""
    keys = ["growth", "inflation", "monetary", "financial"]
    score = 0.0
    norm = 0.0
    mapping = {
        "growth": "growth",
        "inflation": "inflation",
        "monetary": "rates",      # IPS uses 'rates' label
        "financial": "krw",       # KR IPS uses 'krw' for FX/financial conditions
    }
    for k in keys:
        sk = mapping[k]
        sensitivity_v = sensitivity.get(sk, 0)
        score += sensitivity_v * macro_scores.get(k, 0.0)
        norm += abs(sensitivity_v)
    if norm == 0:
        return 0.0
    return float(max(-1.0, min(1.0, score / norm)))


def momentum_signal(prices: pd.Series, lookback: int = 252, skip: int = 21) -> float:
    if prices.dropna().shape[0] < lookback + skip:
        return 0.0
    ret = prices.iloc[-skip - 1] / prices.iloc[-lookback - skip - 1] - 1.0
    return float(np.tanh(2.5 * ret))   # squashing


def trend_signal(prices: pd.Series, fast: int = 50, slow: int = 200) -> float:
    if prices.dropna().shape[0] < slow:
        return 0.0
    f = prices.rolling(fast).mean().iloc[-1]
    s = prices.rolling(slow).mean().iloc[-1]
    if s <= 0:
        return 0.0
    return float(np.tanh(5.0 * (f / s - 1.0)))


def mean_reversion_zscore(prices: pd.Series, window: int = 252) -> float:
    if prices.dropna().shape[0] < window:
        return 0.0
    log_p = np.log(prices)
    m = log_p.rolling(window).mean().iloc[-1]
    sd = log_p.rolling(window).std().iloc[-1]
    if sd <= 0:
        return 0.0
    z = (log_p.iloc[-1] - m) / sd
    return float(-np.tanh(z / 1.5))   # negative -> mean reversion buy


def valuation_signal(cape: float, normal: float = 18.0) -> float:
    if cape is None or cape <= 0:
        return 0.0
    return float(-np.tanh((cape - normal) / 8.0))


def sentiment_signal(seed: int) -> float:
    """Stub: deterministic pseudo-random in [-0.4, 0.4] based on slug seed."""
    rng = np.random.default_rng(seed)
    return float(rng.uniform(-0.4, 0.4))


def aggregate(signals: Dict[str, float]) -> Dict[str, float]:
    """Equal-weight composite over all available signals."""
    if not signals:
        return {"composite": 0.0}
    composite = float(np.mean(list(signals.values())))
    return {**signals, "composite": composite}
