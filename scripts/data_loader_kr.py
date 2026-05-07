"""
KR Pension data loader.

Strategy:
  1. Try yfinance with KR-listed ticker (e.g. "069500.KS").
  2. If a KR ETF has insufficient history (default <504 trading days, ~2y),
     fall back to its proxy ticker (e.g. "SPY" for "TIGER 미국S&P500").
  3. Returns a PriceData panel (prices/returns/monthly) ready for the
     downstream agents.

For currency-hedged ETFs we rely on the proxy (USD-quoted underlying).
For unhedged KR-listed ETFs we use the KR-listed price when available; the
proxy returns are USD-based, so when proxy is the source we are implicitly
ignoring the KRW exposure (acceptable for v1; can be refined later by
multiplying USD returns with USD/KRW pct change).
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

MIN_OBS_KR = 504  # ~2 trading years before we accept KR-listed history


@dataclass
class PriceData:
    prices: pd.DataFrame
    returns: pd.DataFrame
    monthly_returns: pd.DataFrame
    source: str
    provenance: Dict[str, str]  # slug -> "yfinance KR <ticker>" / "yfinance proxy <ticker>"


def _yf_download(ticker: str, start: str, end: Optional[str]) -> Optional[pd.Series]:
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        df = yf.download(
            ticker, start=start, end=end,
            auto_adjust=True, progress=False, threads=False,
        )
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
        else:
            close = df["Close"]
        s = close.dropna()
        return s if len(s) > 0 else None
    except Exception:
        return None


def load_universe_kr(
    asset_classes: List[dict],
    start: str = "1996-01-01",
    end: Optional[str] = None,
    prefer: str = "auto",
    min_obs_kr: int = MIN_OBS_KR,
) -> PriceData:
    """Load price panel for KR pension universe."""
    end = end or datetime.today().strftime("%Y-%m-%d")
    slugs = [ac["slug"] for ac in asset_classes]

    series_map: Dict[str, pd.Series] = {}
    provenance: Dict[str, str] = {}

    for ac in asset_classes:
        slug = ac["slug"]
        kr_ticker = f"{ac['etf']}.KS"
        proxy = ac.get("proxy_ticker")

        kr_series = None
        if prefer in ("auto", "yfinance"):
            kr_series = _yf_download(kr_ticker, start, end)

        # Use KR series if long enough.
        if kr_series is not None and len(kr_series) >= min_obs_kr and proxy is None:
            series_map[slug] = kr_series
            provenance[slug] = f"yfinance KR {kr_ticker} ({len(kr_series)} obs)"
            continue

        # KR is short OR proxy exists → consider proxy.
        if proxy:
            proxy_series = _yf_download(proxy, start, end)
            if proxy_series is not None and len(proxy_series) >= 252:
                # If KR also exists with enough history, splice: use proxy
                # for the long-history portion, KR for the recent portion
                # (proxy aligned so the join point matches).
                if kr_series is not None and len(kr_series) >= min_obs_kr:
                    spliced = _splice(proxy_series, kr_series)
                    series_map[slug] = spliced
                    provenance[slug] = (
                        f"spliced: proxy {proxy} pre-{kr_series.index[0].date()} + "
                        f"KR {kr_ticker} ({len(kr_series)} obs)"
                    )
                else:
                    series_map[slug] = proxy_series
                    provenance[slug] = (
                        f"yfinance proxy {proxy} ({len(proxy_series)} obs) "
                        f"— KR {kr_ticker} insufficient"
                    )
                continue

        # No proxy or proxy failed → use KR even if short.
        if kr_series is not None and len(kr_series) >= 60:
            series_map[slug] = kr_series
            provenance[slug] = f"yfinance KR {kr_ticker} ({len(kr_series)} obs, SHORT)"
            continue

        # Hard miss.
        provenance[slug] = "MISSING — no usable data"

    if not series_map:
        raise RuntimeError("No usable price series fetched for any asset class")

    # Build a unified daily price panel (forward-fill, then drop trailing NA).
    prices = pd.concat(series_map, axis=1).sort_index()
    prices = prices.ffill().dropna(how="all")
    # Reindex to the IPS slug order; missing slugs left as NaN.
    prices = prices.reindex(columns=slugs)

    rets = prices.pct_change().dropna(how="all")
    monthly = prices.resample("M").last().pct_change().dropna(how="all")

    return PriceData(
        prices=prices,
        returns=rets,
        monthly_returns=monthly,
        source="yfinance",
        provenance=provenance,
    )


def _splice(proxy: pd.Series, kr: pd.Series) -> pd.Series:
    """Concat proxy returns prior to KR ETF inception with KR returns thereafter.

    Both series are price levels in their own currency. We rebase the proxy
    so its level on the KR start date equals the KR start price, ensuring a
    smooth join.
    """
    kr_start = kr.index[0]
    proxy_pre = proxy[proxy.index < kr_start]
    if proxy_pre.empty:
        return kr
    # Rebase proxy_pre so its last value matches kr.iloc[0]
    scale = float(kr.iloc[0]) / float(proxy_pre.iloc[-1])
    proxy_pre_rebased = proxy_pre * scale
    return pd.concat([proxy_pre_rebased, kr]).sort_index()


def annualize(returns: pd.DataFrame, periods: int = 252) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for c in returns.columns:
        r = returns[c].dropna()
        if r.empty:
            continue
        mean_ann = float(r.mean() * periods)
        vol_ann = float(r.std(ddof=0) * np.sqrt(periods))
        sharpe = mean_ann / vol_ann if vol_ann > 0 else 0.0
        idx = (1.0 + r).cumprod()
        peaks = idx.cummax()
        dd = float((idx / peaks - 1.0).min())
        out[c] = {
            "mean_ann": mean_ann, "vol_ann": vol_ann,
            "sharpe": sharpe, "max_drawdown": dd,
            "obs": int(r.shape[0]),
        }
    return out


if __name__ == "__main__":
    # Smoke test
    import yaml
    cfg_path = Path(__file__).resolve().parents[1] / "configs" / "ips.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        ips = yaml.safe_load(f)
    data = load_universe_kr(ips["investment_universe"]["asset_classes"], prefer="yfinance")
    print(f"Source: {data.source}, prices shape: {data.prices.shape}")
    print()
    print("=== Provenance ===")
    for slug, prov in data.provenance.items():
        print(f"  {slug:<22} {prov}")
    print()
    print("=== Annualized stats (top 5) ===")
    stats = annualize(data.returns)
    for s, v in list(stats.items())[:5]:
        print(f"  {s:<22} mean={v['mean_ann']*100:6.2f}% vol={v['vol_ann']*100:6.2f}% "
              f"sharpe={v['sharpe']:.2f} mdd={v['max_drawdown']*100:6.1f}% n={v['obs']}")
