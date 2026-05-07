"""
KR macro readings auto-fetcher (ECOS + FRED).

Fetches 15 macro indicators that condition the Korean regime classifier:
  - 12 from ECOS (BOK)         — KR macro
  -  3 from FRED               — global rates / risk-off / oil

Requires ECOS_API_KEY and FRED_API_KEY in env or project-root .env.

Each indicator is wrapped in its own try/except: on failure the static
fallback (representative March-2026 values) remains in place.

ECOS series mapping (verified 2026-04):
  BOK base rate           722Y001 + 0101000   (M)
  KR CPI YoY (등락률)      901Y010 + 00         (M)
  KR CPI level           901Y009 + 0          (M)  [for YoY computation]
  KR unemployment        901Y027 + I61BC      (M)
  KR industrial prod.    901Y033 + A00        (M)
  KR exports (level)     901Y118 + T002       (M)
  KR GDP (real, NSA)     200Y106 + 1400       (Q)
  KTB 10Y                817Y002 + 010210000  (D)
  KTB 3Y                 817Y002 + 010200000  (D)
  Corp AA- 3Y            817Y002 + 010300000  (D)
  USD/KRW                731Y001 + 0000001    (D)
"""
from __future__ import annotations

import datetime as dt
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import requests
from pandas.tseries.offsets import BDay

LOG = logging.getLogger(__name__)

ECOS_BASE = "https://ecos.bok.or.kr/api"
FRED_BASE = "https://api.stlouisfed.org/fred"

# ---------------------------------------------------------------------------
# Static fallback — representative late-cycle KR readings (April 2026)
# ---------------------------------------------------------------------------
KR_FALLBACK_READINGS: Dict[str, float] = {
    # Growth
    "kr_gdp_yoy": 1.5,
    "kr_industrial_production_yoy": 0.5,
    "kr_exports_yoy": 5.0,
    "kr_unemployment": 2.7,
    # Inflation
    "kr_cpi_yoy": 2.5,
    "kr_core_cpi_yoy": 2.2,
    "kr_brent_oil": 95.0,
    "kr_usd_krw": 1380.0,
    # Monetary
    "kr_base_rate": 3.0,
    "kr_ktb_10y": 3.4,
    "kr_ktb_3y": 3.0,
    "kr_curve_3y_10y": 0.4,
    "kr_ktb_10y_change_20d": 0.0,
    "kr_ktb_3y_change_20d": 0.0,
    "kr_curve_3y_10y_change_20d": 0.0,
    # Financial
    "kr_corp_aa_spread_bp": 100.0,
    "us_fed_funds": 4.0,
    "us_vix": 18.0,
}


def _load_env() -> None:
    if os.environ.get("ECOS_API_KEY") and os.environ.get("FRED_API_KEY"):
        return
    for p in [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break


def _parse_ecos_time(t: str, period: str) -> str:
    if period == "D":
        return f"{t[:4]}-{t[4:6]}-{t[6:8]}"
    if period == "M":
        return f"{t[:4]}-{t[4:6]}-01"
    if period == "Q":
        y, q = t[:4], int(t[5])
        m = (q - 1) * 3 + 1
        return f"{y}-{m:02d}-01"
    if period == "A":
        return f"{t}-01-01"
    return t


def _ecos_obs(
    stat_code: str, item_code: str, period: str, n_periods: int = 200,
    timeout: int = 20,
) -> pd.Series:
    api_key = os.environ.get("ECOS_API_KEY")
    if not api_key:
        raise RuntimeError("ECOS_API_KEY not set")

    today = dt.date.today()
    if period == "D":
        end = today.strftime("%Y%m%d")
        start = (today - dt.timedelta(days=120)).strftime("%Y%m%d")
    elif period == "M":
        end = today.strftime("%Y%m")
        sm = today.replace(day=1) - dt.timedelta(days=30 * 24)  # ~24 months back
        start = sm.strftime("%Y%m")
    elif period == "Q":
        q = (today.month - 1) // 3 + 1
        end = f"{today.year}Q{q}"
        start = f"{today.year - 4}Q{q}"
    elif period == "A":
        end = str(today.year)
        start = str(today.year - 6)
    else:
        raise ValueError(f"unknown period: {period}")

    url = (
        f"{ECOS_BASE}/StatisticSearch/{api_key}/json/kr/1/{n_periods}/"
        f"{stat_code}/{period}/{start}/{end}/{item_code}"
    )
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    d = r.json()
    if "StatisticSearch" not in d:
        msg = d.get("RESULT", {}).get("MESSAGE", "no data")
        raise RuntimeError(f"ECOS {stat_code}/{item_code}: {msg}")
    rows = d["StatisticSearch"].get("row", [])
    if not rows:
        return pd.Series(dtype=float)
    pairs = []
    for x in rows:
        v = x.get("DATA_VALUE")
        if v in (None, "", "-"):
            continue
        try:
            pairs.append((_parse_ecos_time(x["TIME"], period), float(v)))
        except Exception:
            continue
    if not pairs:
        return pd.Series(dtype=float)
    s = pd.Series(
        [v for _, v in pairs],
        index=pd.to_datetime([d for d, _ in pairs]),
    ).sort_index()
    return s


def _fred_obs(series_id: str, limit: int = 5, timeout: int = 20) -> pd.Series:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY not set")
    url = (
        f"{FRED_BASE}/series/observations"
        f"?series_id={series_id}&api_key={api_key}"
        f"&file_type=json&sort_order=desc&limit={limit}"
    )
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    obs = r.json().get("observations", [])
    rows = [(o["date"], o["value"]) for o in obs if o.get("value") not in (None, ".", "")]
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series(
        [float(v) for _, v in rows],
        index=pd.to_datetime([d for d, _ in rows]),
    ).sort_index()
    return s


# ---------------------------------------------------------------------------
# Historical fetch helpers (for walk-forward backtest)
# ---------------------------------------------------------------------------
def _ecos_history(
    stat_code: str, item_code: str, period: str,
    start_date: str = "2010-01-01", n_periods: int = 10000,
    timeout: int = 30,
) -> pd.Series:
    """ECOS full-series fetch from `start_date` to today.

    Mirrors `_ecos_obs` but with explicit start, large n_periods, and
    longer timeout for big pulls (e.g., daily KTB rates 2010~2026).
    """
    api_key = os.environ.get("ECOS_API_KEY")
    if not api_key:
        raise RuntimeError("ECOS_API_KEY not set")

    sd = pd.Timestamp(start_date)
    ed = pd.Timestamp.today()
    if period == "D":
        start, end = sd.strftime("%Y%m%d"), ed.strftime("%Y%m%d")
    elif period == "M":
        start, end = sd.strftime("%Y%m"), ed.strftime("%Y%m")
    elif period == "Q":
        sq, eq = (sd.month - 1) // 3 + 1, (ed.month - 1) // 3 + 1
        start, end = f"{sd.year}Q{sq}", f"{ed.year}Q{eq}"
    elif period == "A":
        start, end = str(sd.year), str(ed.year)
    else:
        raise ValueError(f"unknown period: {period}")

    url = (
        f"{ECOS_BASE}/StatisticSearch/{api_key}/json/kr/1/{n_periods}/"
        f"{stat_code}/{period}/{start}/{end}/{item_code}"
    )
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    d = r.json()
    if "StatisticSearch" not in d:
        msg = d.get("RESULT", {}).get("MESSAGE", "no data")
        raise RuntimeError(f"ECOS {stat_code}/{item_code}: {msg}")
    rows = d["StatisticSearch"].get("row", [])
    if not rows:
        return pd.Series(dtype=float)
    pairs = []
    for x in rows:
        v = x.get("DATA_VALUE")
        if v in (None, "", "-"):
            continue
        try:
            pairs.append((_parse_ecos_time(x["TIME"], period), float(v)))
        except Exception:
            continue
    if not pairs:
        return pd.Series(dtype=float)
    return pd.Series(
        [v for _, v in pairs],
        index=pd.to_datetime([d for d, _ in pairs]),
    ).sort_index()


def _fred_history(series_id: str, start: str = "2010-01-01", timeout: int = 30) -> pd.Series:
    """FRED full-series fetch from `start` onward, ascending."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY not set")
    url = (
        f"{FRED_BASE}/series/observations"
        f"?series_id={series_id}&api_key={api_key}"
        f"&file_type=json&observation_start={start}&sort_order=asc"
    )
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    obs = r.json().get("observations", [])
    rows = [(o["date"], o["value"]) for o in obs if o.get("value") not in (None, ".", "")]
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series(
        [float(v) for _, v in rows],
        index=pd.to_datetime([d for d, _ in rows]),
    ).sort_index()


# Publication lag (months) for each KR/global series we use as_of date `t`.
# Daily market series (rates, FX, oil, VIX) have no lag.
# Monthly survey/macro (CPI, unemployment, IP) have ~1 month publication lag.
# Quarterly GDP has ~2.5 months lag (advance ≈ 1 month after Q-end, final ~3m).
_KR_LAG_MONTHS = {
    # ECOS keys (stat_code + item_code → tag for our panel dict)
    "kr_gdp_yoy": 3,
    "kr_industrial_production_yoy": 1,
    "kr_exports_yoy": 1,
    "kr_unemployment": 1,
    "kr_cpi_yoy": 1,
    # Daily market — no lag
    "kr_base_rate": 0,
    "kr_ktb_10y": 0,
    "kr_ktb_3y": 0,
    "kr_corp_aa_3y": 0,
    "kr_usd_krw": 0,
    # FRED daily
    "us_fed_funds": 0,
    "us_vix": 0,
    "kr_brent_oil": 0,
}


def historical_macro_panel_kr(start: str = "2010-01-01") -> Dict[str, pd.Series]:
    """Bulk-fetch every KR + global macro series we use, once.

    Returns a dict keyed by readings-key (e.g., "kr_gdp_yoy" stores the
    quarterly GDP level series; YoY computation happens in `readings_as_of_kr`).
    For daily/monthly point measurements (rates, FX, unemployment) the value
    is the level series itself.

    Use this once at backtest setup; then call `readings_as_of_kr(panel, t)`
    per quarter.
    """
    _load_env()
    panel: Dict[str, pd.Series] = {}

    # ECOS specs: (panel_key, stat_code, item_code, period)
    ecos_specs = [
        ("kr_gdp_level",        "200Y106", "1400",      "Q"),  # real GDP NSA → YoY computed
        ("kr_ip_level",         "901Y033", "A00",       "M"),  # IP → YoY computed
        ("kr_exports_level",    "901Y118", "T002",      "M"),  # exports → YoY computed
        ("kr_unemployment",     "901Y027", "I61BC",     "M"),
        ("kr_cpi_level",        "901Y009", "0",         "M"),  # CPI level → YoY computed
        ("kr_base_rate",        "722Y001", "0101000",   "M"),
        ("kr_ktb_10y",          "817Y002", "010210000", "D"),
        ("kr_ktb_3y",           "817Y002", "010200000", "D"),
        ("kr_corp_aa_3y",       "817Y002", "010300000", "D"),
        ("kr_usd_krw",          "731Y001", "0000001",   "D"),
    ]
    for key, stat, item, per in ecos_specs:
        try:
            s = _ecos_history(stat, item, per, start_date=start)
            panel[key] = s
            LOG.info("ECOS %s: %d obs from %s",
                     key, len(s),
                     s.index[0].date() if len(s) else "(empty)")
        except Exception as e:
            LOG.warning("ECOS %s/%s history failed: %s", stat, item, e)
            panel[key] = pd.Series(dtype=float)

    # FRED globals
    fred_specs = [
        ("us_fed_funds",  "DFF"),
        ("us_vix",        "VIXCLS"),
        ("kr_brent_oil",  "DCOILBRENTEU"),
    ]
    for key, sid in fred_specs:
        try:
            s = _fred_history(sid, start=start)
            panel[key] = s
            LOG.info("FRED %s: %d obs from %s",
                     key, len(s),
                     s.index[0].date() if len(s) else "(empty)")
        except Exception as e:
            LOG.warning("FRED %s history failed: %s", sid, e)
            panel[key] = pd.Series(dtype=float)

    return panel


def _latest_before(s: pd.Series, asof: pd.Timestamp, lag_months: int = 0) -> Optional[float]:
    if s is None or len(s) == 0:
        return None
    cutoff = asof - pd.DateOffset(months=lag_months)
    sub = s[s.index <= cutoff]
    return float(sub.iloc[-1]) if len(sub) else None


def _change_over_bdays(
    s: pd.Series,
    asof: pd.Timestamp,
    bdays: int,
    lag_months: int = 0,
) -> Optional[float]:
    if s is None or len(s) == 0:
        return None
    cutoff = asof - pd.DateOffset(months=lag_months)
    sub = s[s.index <= cutoff]
    if len(sub) < 2:
        return None
    prev = sub[sub.index <= cutoff - BDay(bdays)]
    if len(prev) == 0:
        return None
    return float(sub.iloc[-1] - prev.iloc[-1])


def readings_as_of_kr(
    panel: Dict[str, pd.Series],
    as_of_date,
    static_fallback: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Build a KR macro readings dict from cached `panel`, as known on `as_of_date`.

    Uses publication-lag aware slicing so the historical reading reflects what
    was actually known to a real-time observer on `as_of_date`.
    """
    out: Dict[str, float] = dict(static_fallback or KR_FALLBACK_READINGS)
    asof = pd.Timestamp(as_of_date)

    # GDP YoY% — need 5 quarterly obs ending at (asof - 3m).
    s = panel.get("kr_gdp_level")
    if s is not None and len(s):
        cutoff = asof - pd.DateOffset(months=_KR_LAG_MONTHS["kr_gdp_yoy"])
        sub = s[s.index <= cutoff]
        if len(sub) >= 5:
            out["kr_gdp_yoy"] = round(float((sub.iloc[-1] / sub.iloc[-5] - 1.0) * 100), 2)

    # IP YoY%, Exports YoY%, CPI YoY% — need 13 monthly obs ending at (asof - 1m).
    for out_key, panel_key in [
        ("kr_industrial_production_yoy", "kr_ip_level"),
        ("kr_exports_yoy",               "kr_exports_level"),
        ("kr_cpi_yoy",                   "kr_cpi_level"),
    ]:
        s = panel.get(panel_key)
        if s is not None and len(s):
            cutoff = asof - pd.DateOffset(months=_KR_LAG_MONTHS[out_key])
            sub = s[s.index <= cutoff]
            if len(sub) >= 13:
                out[out_key] = round(float((sub.iloc[-1] / sub.iloc[-13] - 1.0) * 100), 2)

    # Latest-value point measurements.
    for key in ["kr_unemployment", "kr_base_rate",
                "kr_ktb_10y", "kr_ktb_3y", "kr_usd_krw",
                "us_fed_funds", "us_vix", "kr_brent_oil"]:
        v = _latest_before(panel.get(key), asof, _KR_LAG_MONTHS.get(key, 0))
        if v is not None:
            out[key] = round(v, 2 if "rate" not in key and key != "kr_usd_krw" else (2 if "rate" in key else 1))

    # Derived: KTB term spread + Corp AA- spread.
    if "kr_ktb_10y" in out and "kr_ktb_3y" in out:
        out["kr_curve_3y_10y"] = round(out["kr_ktb_10y"] - out["kr_ktb_3y"], 3)
    for out_key, panel_key in [
        ("kr_ktb_10y_change_20d", "kr_ktb_10y"),
        ("kr_ktb_3y_change_20d", "kr_ktb_3y"),
    ]:
        delta = _change_over_bdays(panel.get(panel_key), asof, 20, _KR_LAG_MONTHS.get(panel_key, 0))
        if delta is not None:
            out[out_key] = round(delta, 3)
    if "kr_ktb_10y_change_20d" in out and "kr_ktb_3y_change_20d" in out:
        out["kr_curve_3y_10y_change_20d"] = round(
            out["kr_ktb_10y_change_20d"] - out["kr_ktb_3y_change_20d"], 3
        )
    corp_aa = _latest_before(panel.get("kr_corp_aa_3y"), asof, 0)
    if corp_aa is not None and "kr_ktb_3y" in out:
        out["kr_corp_aa_spread_bp"] = round((corp_aa - out["kr_ktb_3y"]) * 100, 0)

    return out


def fetch_latest_macro_readings_kr(
    static_fallback: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Build the KR macro readings dict.

    Starts from `static_fallback`, then overwrites each entry that we can
    fetch live. Provenance recorded under `_fetch_provenance`.
    """
    _load_env()
    out: Dict[str, float] = dict(static_fallback or KR_FALLBACK_READINGS)
    fetched: Dict[str, str] = {}

    # ---- KR Growth ----
    # GDP YoY% from quarterly real GDP (NSA, ITEM_CODE 1400).
    try:
        gdp = _ecos_obs("200Y106", "1400", "Q", n_periods=200)
        if len(gdp) >= 5:
            out["kr_gdp_yoy"] = round(float((gdp.iloc[-1] / gdp.iloc[-5] - 1.0) * 100), 2)
            fetched["kr_gdp_yoy"] = f"ECOS 200Y106/1400 @ {gdp.index[-1].date()}"
    except Exception as e:
        LOG.warning("KR GDP fetch failed: %s", e)

    # Industrial production YoY% (전산업생산지수 A00).
    try:
        ip = _ecos_obs("901Y033", "A00", "M", n_periods=200)
        if len(ip) >= 13:
            out["kr_industrial_production_yoy"] = round(
                float((ip.iloc[-1] / ip.iloc[-13] - 1.0) * 100), 2)
            fetched["kr_industrial_production_yoy"] = (
                f"ECOS 901Y033/A00 @ {ip.index[-1].date()}"
            )
    except Exception as e:
        LOG.warning("KR IP fetch failed: %s", e)

    # Exports YoY% (수출금액 T002).
    try:
        exp = _ecos_obs("901Y118", "T002", "M", n_periods=200)
        if len(exp) >= 13:
            out["kr_exports_yoy"] = round(
                float((exp.iloc[-1] / exp.iloc[-13] - 1.0) * 100), 2)
            fetched["kr_exports_yoy"] = f"ECOS 901Y118/T002 @ {exp.index[-1].date()}"
    except Exception as e:
        LOG.warning("KR exports fetch failed: %s", e)

    # Unemployment rate (실업률 I61BC).
    try:
        ur = _ecos_obs("901Y027", "I61BC", "M", n_periods=200)
        if len(ur):
            out["kr_unemployment"] = round(float(ur.iloc[-1]), 2)
            fetched["kr_unemployment"] = f"ECOS 901Y027/I61BC @ {ur.index[-1].date()}"
    except Exception as e:
        LOG.warning("KR UR fetch failed: %s", e)

    # ---- KR Inflation ----
    # CPI YoY% — fetch 14+ months of CPI level (901Y009/0) and compute YoY.
    try:
        cpi = _ecos_obs("901Y009", "0", "M", n_periods=200)
        if len(cpi) >= 13:
            out["kr_cpi_yoy"] = round(float((cpi.iloc[-1] / cpi.iloc[-13] - 1.0) * 100), 2)
            fetched["kr_cpi_yoy"] = f"ECOS 901Y009/0 @ {cpi.index[-1].date()} (YoY computed)"
    except Exception as e:
        LOG.warning("KR CPI fetch failed: %s", e)

    # USD/KRW (원/달러 매매기준율).
    try:
        fx = _ecos_obs("731Y001", "0000001", "D", n_periods=200)
        if len(fx):
            out["kr_usd_krw"] = round(float(fx.iloc[-1]), 1)
            fetched["kr_usd_krw"] = f"ECOS 731Y001/0000001 @ {fx.index[-1].date()}"
    except Exception as e:
        LOG.warning("USD/KRW fetch failed: %s", e)

    # ---- KR Monetary ----
    # BOK base rate.
    try:
        br = _ecos_obs("722Y001", "0101000", "M", n_periods=200)
        if len(br):
            out["kr_base_rate"] = round(float(br.iloc[-1]), 2)
            fetched["kr_base_rate"] = f"ECOS 722Y001/0101000 @ {br.index[-1].date()}"
    except Exception as e:
        LOG.warning("BOK rate fetch failed: %s", e)

    # KTB 10Y / 3Y / Corp AA- 3Y.
    ktb_10y_val = None
    ktb_3y_val = None
    ktb_10y_delta = None
    ktb_3y_delta = None
    corp_aa_val = None
    for key, item in [
        ("kr_ktb_10y", "010210000"),
        ("kr_ktb_3y", "010200000"),
        ("kr_corp_aa", "010300000"),
    ]:
        try:
            s = _ecos_obs("817Y002", item, "D", n_periods=200)
            if len(s):
                v = round(float(s.iloc[-1]), 3)
                if key == "kr_ktb_10y":
                    out["kr_ktb_10y"] = v
                    ktb_10y_val = v
                    prev = s[s.index <= s.index[-1] - BDay(20)]
                    if len(prev):
                        ktb_10y_delta = round(float(s.iloc[-1] - prev.iloc[-1]), 3)
                    fetched["kr_ktb_10y"] = f"ECOS 817Y002/{item} @ {s.index[-1].date()}"
                elif key == "kr_ktb_3y":
                    out["kr_ktb_3y"] = v
                    ktb_3y_val = v
                    prev = s[s.index <= s.index[-1] - BDay(20)]
                    if len(prev):
                        ktb_3y_delta = round(float(s.iloc[-1] - prev.iloc[-1]), 3)
                    fetched["kr_ktb_3y"] = f"ECOS 817Y002/{item} @ {s.index[-1].date()}"
                else:
                    corp_aa_val = v
        except Exception as e:
            LOG.warning("ECOS %s fetch failed: %s", item, e)

    # Derived: 3y/10y curve and Corp AA- spread.
    if ktb_10y_val is not None and ktb_3y_val is not None:
        out["kr_curve_3y_10y"] = round(ktb_10y_val - ktb_3y_val, 3)
        fetched["kr_curve_3y_10y"] = "derived: KTB 10Y - KTB 3Y"
    if ktb_10y_delta is not None:
        out["kr_ktb_10y_change_20d"] = ktb_10y_delta
        fetched["kr_ktb_10y_change_20d"] = "derived: KTB 10Y 20-business-day change"
    if ktb_3y_delta is not None:
        out["kr_ktb_3y_change_20d"] = ktb_3y_delta
        fetched["kr_ktb_3y_change_20d"] = "derived: KTB 3Y 20-business-day change"
    if ktb_10y_delta is not None and ktb_3y_delta is not None:
        out["kr_curve_3y_10y_change_20d"] = round(ktb_10y_delta - ktb_3y_delta, 3)
        fetched["kr_curve_3y_10y_change_20d"] = "derived: (KTB 10Y - KTB 3Y) 20-business-day change"
    if corp_aa_val is not None and ktb_3y_val is not None:
        out["kr_corp_aa_spread_bp"] = round((corp_aa_val - ktb_3y_val) * 100, 0)
        fetched["kr_corp_aa_spread_bp"] = "derived: (Corp AA- 3Y - KTB 3Y) × 100"

    # ---- Global (FRED) ----
    for key, sid, transform in [
        ("us_fed_funds", "DFF", lambda v: round(v, 2)),
        ("us_vix", "VIXCLS", lambda v: round(v, 2)),
        ("kr_brent_oil", "DCOILBRENTEU", lambda v: round(v, 2)),
    ]:
        try:
            s = _fred_obs(sid, limit=5)
            if len(s):
                out[key] = transform(float(s.iloc[-1]))
                fetched[key] = f"FRED {sid} @ {s.index[-1].date()}"
        except Exception as e:
            LOG.warning("FRED %s fetch failed: %s", sid, e)

    # kr_core_cpi_yoy : ECOS does not have a single clean "agri+oil 제외" series
    # exposed via the same shape. Leaving the static fallback for v1; can be
    # added later by drilling into 901Y010 sub-items.

    out["_fetch_provenance"] = fetched
    return out


if __name__ == "__main__":
    print("=== Static fallback ===")
    for k, v in KR_FALLBACK_READINGS.items():
        print(f"  {k:30s} = {v}")
    print()
    print("=== Live fetch ===")
    live = fetch_latest_macro_readings_kr(KR_FALLBACK_READINGS)
    prov = live.pop("_fetch_provenance", {})
    for k, v in live.items():
        tag = f"  [{prov[k]}]" if k in prov else "  [static fallback]"
        print(f"  {k:30s} = {v}{tag}")
