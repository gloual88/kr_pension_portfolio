"""
Korean macro regime classifier.

Four dimensions (growth / inflation / monetary / financial), scored from
ECOS + FRED readings. Mirrors the structure of `regime_v2.py` but
calibrated to Korean macro normals (BOK rates, KTB curve, USD/KRW band,
exports cycle, KR HY-credit proxy).

Reference normals (rough, 2015-2025 averages):
  GDP YoY            2.5
  IP YoY             1.5
  Exports YoY        5.0
  Unemployment       3.5
  CPI YoY            2.0
  Core CPI YoY       2.0
  Brent oil          75
  USD/KRW            1300
  BOK base rate      2.5
  KTB 10Y            3.0
  Curve 3Y/10Y       0.4
  Corp AA- spread bp 80
  Fed funds          2.5
  VIX                18
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


KR_DEFAULT_READINGS: Dict[str, float] = {
    "kr_gdp_yoy": 1.5,
    "kr_industrial_production_yoy": 0.5,
    "kr_exports_yoy": 5.0,
    "kr_unemployment": 2.7,
    "kr_cpi_yoy": 2.5,
    "kr_core_cpi_yoy": 2.2,
    "kr_brent_oil": 95.0,
    "kr_usd_krw": 1380.0,
    "kr_base_rate": 3.0,
    "kr_ktb_10y": 3.4,
    "kr_ktb_3y": 3.0,
    "kr_curve_3y_10y": 0.4,
    "kr_ktb_10y_change_20d": 0.0,
    "kr_ktb_3y_change_20d": 0.0,
    "kr_curve_3y_10y_change_20d": 0.0,
    "kr_corp_aa_spread_bp": 100.0,
    "us_fed_funds": 4.0,
    "us_vix": 18.0,
}


@dataclass
class RegimeResultKR:
    regime: str
    confidence: float
    scores: Dict[str, float]
    notes: str


def classify_curve_signal_kr(readings: Dict[str, float] | None = None) -> Dict[str, Any]:
    r = readings or KR_DEFAULT_READINGS
    slope = float(r.get("kr_curve_3y_10y", 0.0))
    delta_10y = float(r.get("kr_ktb_10y_change_20d", 0.0))
    delta_3y = float(r.get("kr_ktb_3y_change_20d", 0.0))
    curve_delta = float(r.get("kr_curve_3y_10y_change_20d", delta_10y - delta_3y))
    avg_rate_delta = 0.5 * (delta_10y + delta_3y)

    if slope < 0.0:
        shape = "inverted"
    elif slope < 0.15:
        shape = "flat"
    elif slope < 0.50:
        shape = "normal"
    else:
        shape = "steep"

    if avg_rate_delta >= 0.08:
        move = "bear"
    elif avg_rate_delta <= -0.08:
        move = "bull"
    else:
        move = "stable"

    if curve_delta >= 0.05:
        twist = "steepening"
    elif curve_delta <= -0.05:
        twist = "flattening"
    else:
        twist = "parallel"

    if move == "stable":
        regime = "range-bound" if twist == "parallel" else f"static-{twist}"
    else:
        regime = f"{move}-{twist}"

    notes = (
        f"KTB 3Y-10Y {slope*100:+.0f}bp, 20d d3Y {delta_3y*100:+.0f}bp, "
        f"d10Y {delta_10y*100:+.0f}bp, curve d {curve_delta*100:+.0f}bp "
        f"-> {regime} ({shape})."
    )
    return {
        "regime": regime,
        "shape": shape,
        "move": move,
        "twist": twist,
        "slope": round(slope, 3),
        "slope_bp": round(slope * 100, 1),
        "avg_rate_change_20d": round(avg_rate_delta, 3),
        "avg_rate_change_20d_bp": round(avg_rate_delta * 100, 1),
        "curve_change_20d": round(curve_delta, 3),
        "curve_change_20d_bp": round(curve_delta * 100, 1),
        "notes": notes,
    }


def _norm(x: float, center: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    return max(-1.0, min(1.0, (x - center) / scale))


def _score_growth(r: Dict[str, float]) -> float:
    s = 0.0
    s += _norm(r["kr_gdp_yoy"], 2.5, 1.5)
    s += _norm(r["kr_industrial_production_yoy"], 1.5, 3.0)
    s += _norm(r["kr_exports_yoy"], 5.0, 8.0)
    # Unemployment: lower = stronger growth (KR natural ~3.5%).
    s += _norm(-(r["kr_unemployment"] - 3.5), 0, 0.7)
    return float(s / 4.0)


def _score_inflation(r: Dict[str, float]) -> float:
    s = 0.0
    s += _norm(r["kr_cpi_yoy"], 2.0, 1.0)
    s += _norm(r["kr_core_cpi_yoy"], 2.0, 1.0)
    # Oil and FX feed import-led inflation in KR (high import dependency).
    s += _norm(r["kr_brent_oil"] - 75, 0, 25)
    s += _norm(r["kr_usd_krw"] - 1300, 0, 100)
    return float(s / 4.0)


def _score_monetary(r: Dict[str, float]) -> float:
    """Higher score = looser policy (more accommodative)."""
    s = 0.0
    # BOK rate above 2.5% normal = restrictive = negative.
    s += -_norm(r["kr_base_rate"] - 2.5, 0, 1.0)
    # KTB 10Y above 3.0% normal = restrictive = negative.
    s += -_norm(r["kr_ktb_10y"] - 3.0, 0, 1.0)
    # Steeper curve = looser (forward-looking).
    s += _norm(r["kr_curve_3y_10y"], 0.5, 0.5)
    # US Fed funds: KR is partly anchored by Fed; restrictive Fed = negative.
    s += -_norm(r["us_fed_funds"] - 2.5, 0, 1.5)
    return float(s / 4.0)


def _score_financial(r: Dict[str, float]) -> float:
    """Higher score = healthier financial conditions (lower stress)."""
    s = 0.0
    # KR Corp AA- spread above 80bp normal = stress = negative.
    s += -_norm(r["kr_corp_aa_spread_bp"] - 80, 0, 80)
    # VIX above 18 normal = global stress = negative.
    s += -_norm(r["us_vix"] - 18, 0, 10)
    # USD/KRW above 1300 normal = capital outflow / risk-off = negative.
    s += -_norm(r["kr_usd_krw"] - 1300, 0, 100)
    return float(s / 3.0)


def classify_regime_kr(readings: Dict[str, float] = None) -> RegimeResultKR:
    r = readings or KR_DEFAULT_READINGS
    g = _score_growth(r)
    i = _score_inflation(r)
    m = _score_monetary(r)
    f = _score_financial(r)
    scores = {"growth": g, "inflation": i, "monetary": m, "financial": f}

    # Stagflationary late-cycle (KR-specific): inflation > 0, monetary < 0,
    # growth not collapsing. KR-specific: oil shock + KRW weakness pattern.
    stagflationary = (i >= 0.0) and (m <= -0.3) and (f <= 0.0)

    if (g > 0.2) and (i < 0.0) and (m > 0.0) and (f > 0.0):
        regime = "expansion"
    elif stagflationary and (g >= -0.5):
        regime = "late-cycle"
    elif (g < -0.5) and (m < -0.3) and (f < -0.1):
        regime = "recession"
    elif (g > 0.0) and (m < -0.1) and (i < 0.2) and (f >= 0.0):
        regime = "recovery"
    else:
        templates = {
            "expansion":  {"growth": 1, "inflation": -1, "monetary": 1, "financial": 1},
            "late-cycle": {"growth": 0, "inflation": 1, "monetary": -1, "financial": -1},
            "recession":  {"growth": -1, "inflation": 0, "monetary": -1, "financial": -1},
            "recovery":   {"growth": 1, "inflation": -1, "monetary": -1, "financial": 1},
        }
        best, bestd = None, 1e9
        for name, tmpl in templates.items():
            d = sum((tmpl[k] - scores[k]) ** 2 for k in scores)
            if d < bestd:
                bestd, best = d, name
        regime = best or "late-cycle"

    conf = float(min(1.0, max(0.0, sum(abs(v) for v in scores.values()) / 4.0)))
    notes = (
        f"성장 GDP {r['kr_gdp_yoy']:+.1f}%, 수출 {r['kr_exports_yoy']:+.1f}%, "
        f"실업 {r['kr_unemployment']:.1f}%. "
        f"인플레 CPI {r['kr_cpi_yoy']:+.1f}%, 유가 ${r['kr_brent_oil']:.0f}, "
        f"USD/KRW {r['kr_usd_krw']:.0f}. "
        f"BOK {r['kr_base_rate']:.2f}%, KTB10Y {r['kr_ktb_10y']:.2f}%, "
        f"AA-spread {r['kr_corp_aa_spread_bp']:.0f}bp, VIX {r['us_vix']:.1f}."
    )
    return RegimeResultKR(regime=regime, confidence=conf, scores=scores, notes=notes)


def recession_probability_kr(readings: Dict[str, float] = None) -> float:
    """Heuristic 12-month KR recession probability."""
    r = readings or KR_DEFAULT_READINGS
    p = 0.20
    if r["kr_curve_3y_10y"] < 0.0:
        p += 0.06
    if r["kr_exports_yoy"] < 0:
        p += 0.07
    if r["kr_industrial_production_yoy"] < 0:
        p += 0.05
    if r["kr_corp_aa_spread_bp"] > 200:
        p += 0.04
    if r["us_vix"] > 28:
        p += 0.04
    if r["kr_unemployment"] > 4.0:
        p += 0.04
    return min(0.50, p)
