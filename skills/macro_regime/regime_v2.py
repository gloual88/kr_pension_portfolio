"""
Macro regime classifier — v2 (fresh module to side-step a stale .pyc on the
caller's filesystem). Logic mirrors regime_classifier.py but the late-cycle
predicate now matches the stagflationary description in Section 4.1 of the
paper: positive inflation, negative monetary score, weak financial conditions,
and growth that is decelerating but not collapsing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


MARCH_2026_READINGS_V2: Dict[str, float] = {
    "real_gdp_yoy": 1.4,
    "nonfarm_payrolls_3m": -25,
    "ism_manufacturing": 48.7,
    "cpi_yoy": 2.4,
    "core_cpi_yoy": 2.5,
    "unemployment": 4.4,
    "fed_funds": 3.75,
    "ten_year": 4.05,
    "twos_tens": 0.10,
    "hy_oas_bp": 425,
    "vix": 22.5,
    "usd_index": 99.8,
    "brent_oil": 88.2,
    "breakevens_5y": 2.65,
}


@dataclass
class RegimeResultV2:
    regime: str
    confidence: float
    scores: Dict[str, float]
    notes: str


def _norm_v2(x: float, center: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    z = (x - center) / scale
    return max(-1.0, min(1.0, z))


def _score_growth_v2(r):
    s = 0.0
    s += _norm_v2(r["real_gdp_yoy"], 1.5, 1.5)
    s += _norm_v2(r["nonfarm_payrolls_3m"], 100, 150)
    s += _norm_v2(r["ism_manufacturing"], 50, 5)
    s += _norm_v2(-(r["unemployment"] - 4.0), 0, 1.0)
    return float(s / 4.0)


def _score_inflation_v2(r):
    s = 0.0
    s += _norm_v2(r["cpi_yoy"], 2.0, 1.0)
    s += _norm_v2(r["core_cpi_yoy"], 2.0, 1.0)
    s += _norm_v2(r["breakevens_5y"], 2.5, 0.5)
    s += _norm_v2(r["brent_oil"] - 75, 0, 25)
    return float(s / 4.0)


def _score_monetary_v2(r):
    s = 0.0
    s += -_norm_v2(r["fed_funds"] - 2.5, 0, 1.5)
    s += -_norm_v2(r["ten_year"] - 3.5, 0, 1.5)
    s += _norm_v2(r["twos_tens"], 0.5, 0.5)
    return float(s / 3.0)


def _score_financial_v2(r):
    s = 0.0
    s += -_norm_v2(r["hy_oas_bp"] - 350, 0, 200)
    s += -_norm_v2(r["vix"] - 18, 0, 10)
    s += -_norm_v2(r["usd_index"] - 100, 0, 5)
    return float(s / 3.0)


def classify_regime_v2(readings: Dict[str, float] = None) -> RegimeResultV2:
    r = readings or MARCH_2026_READINGS_V2
    g = _score_growth_v2(r)
    i = _score_inflation_v2(r)
    m = _score_monetary_v2(r)
    f = _score_financial_v2(r)
    scores = {"growth": g, "inflation": i, "monetary": m, "financial": f}

    # Stagflationary late-cycle: high inflation + restrictive policy + weak
    # financial conditions, even if growth is sub-trend (paper Section 4.1).
    stagflationary = (i >= 0.0) and (m <= -0.4) and (f <= -0.1)

    if (g > 0.0) and (i < 0.0) and (m > 0.0) and (f > 0.0):
        regime = "expansion"
    elif stagflationary and (g >= -0.5):
        regime = "late-cycle"
    elif (g < -0.5) and (m < -0.3) and (f < -0.1):
        regime = "recession"
    elif (g > 0.0) and (m < -0.1) and (i < 0.2) and (f >= 0.0):
        regime = "recovery"
    else:
        templates = {
            "expansion":   {"growth": 1, "inflation": -1, "monetary": 1, "financial": 1},
            "late-cycle":  {"growth": 0, "inflation": 1, "monetary": -1, "financial": -1},
            "recession":   {"growth": -1, "inflation": 0, "monetary": -1, "financial": -1},
            "recovery":    {"growth": 1, "inflation": -1, "monetary": -1, "financial": 1},
        }
        best, bestd = None, 1e9
        for name, tmpl in templates.items():
            d = sum((tmpl[k] - scores[k]) ** 2 for k in scores)
            if d < bestd:
                bestd, best = d, name
        regime = best or "late-cycle"

    conf = float(min(1.0, max(0.0, sum(abs(v) for v in scores.values()) / 4.0)))
    notes = (
        f"Growth decel (GDP {r['real_gdp_yoy']:.1f}%, payrolls {r['nonfarm_payrolls_3m']:+.0f}k/3m). "
        f"Inflation {r['cpi_yoy']:.1f}% with oil shock to ${r['brent_oil']:.0f}. "
        f"Policy still restrictive (FF {r['fed_funds']:.2f}%). "
        f"Spreads {r['hy_oas_bp']:.0f}bp, VIX {r['vix']:.1f}."
    )
    return RegimeResultV2(regime=regime, confidence=conf, scores=scores, notes=notes)


def recession_probability_v2(readings: Dict[str, float] = None) -> float:
    r = readings or MARCH_2026_READINGS_V2
    p = 0.20
    if r["twos_tens"] < 0.5:
        p += 0.05
    if r["nonfarm_payrolls_3m"] < 0:
        p += 0.07
    if r["ism_manufacturing"] < 50:
        p += 0.05
    if r["hy_oas_bp"] > 400:
        p += 0.03
    return min(0.50, p)
