"""Historical statistics: returns, vol, correlations, drawdown."""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd


def summary_stats(returns: pd.DataFrame, periods: int = 252) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for c in returns.columns:
        r = returns[c].dropna()
        mean_ann = float(r.mean() * periods)
        vol_ann = float(r.std(ddof=0) * np.sqrt(periods))
        sharpe = mean_ann / vol_ann if vol_ann > 0 else 0.0
        idx = (1.0 + r).cumprod()
        peak = idx.cummax()
        dd = float((idx / peak - 1.0).min())
        out[c] = {
            "mean_ann": mean_ann,
            "vol_ann": vol_ann,
            "sharpe": sharpe,
            "skew": float(r.skew()),
            "kurtosis": float(r.kurt()),
            "max_drawdown": dd,
            "obs": int(r.shape[0]),
        }
    return out


def correlation_matrix(returns: pd.DataFrame, halflife: Optional[int] = None) -> pd.DataFrame:
    if halflife is None:
        return returns.corr()
    return returns.ewm(halflife=halflife, min_periods=20).cov().groupby(level=1).last().corr()


def rolling_volatility(returns: pd.DataFrame, window: int = 63, periods: int = 252) -> pd.DataFrame:
    return returns.rolling(window).std() * np.sqrt(periods)


def historical_erp(equity_returns: pd.Series, rf_returns: pd.Series) -> float:
    """Geometric equity risk premium."""
    aligned = pd.concat([equity_returns, rf_returns], axis=1, join="inner").dropna()
    if aligned.shape[0] < 60:
        return 0.05
    eq, rf = aligned.iloc[:, 0], aligned.iloc[:, 1]
    ann = 252
    eq_ann = (1 + eq).prod() ** (ann / len(eq)) - 1
    rf_ann = (1 + rf).prod() ** (ann / len(rf)) - 1
    return float(eq_ann - rf_ann)


def drawdown_profile(returns: pd.Series) -> Dict[str, float]:
    idx = (1.0 + returns).cumprod()
    peak = idx.cummax()
    dd = idx / peak - 1.0
    max_dd = float(dd.min())
    underwater = (dd < 0).astype(int)
    if underwater.sum() == 0:
        max_dur = 0
    else:
        # longest consecutive underwater streak
        groups = (underwater != underwater.shift()).cumsum()
        durations = underwater.groupby(groups).sum()
        max_dur = int(durations.max())
    return {"max_drawdown": max_dd, "max_drawdown_days": max_dur}


def covariance_matrix(returns: pd.DataFrame, periods: int = 252, halflife: Optional[int] = None) -> pd.DataFrame:
    if halflife is None:
        return returns.cov() * periods
    cov = returns.ewm(halflife=halflife, min_periods=60).cov()
    last_idx = cov.index.get_level_values(0).unique()[-1]
    return cov.xs(last_idx) * periods
