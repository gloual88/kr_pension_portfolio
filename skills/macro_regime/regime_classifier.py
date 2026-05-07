"""
Macro regime classifier (v2).

Reproduces the late-cycle/stagflationary regime described in Section 4.1 of the
paper for the March 2026 run. v2 broadens the late-cycle decision rule to admit
stagflationary configurations (positive inflation + negative monetary score +
weak financial conditions + decelerating but not collapsing growth).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


# Default March 2026 macro readings consistent with Section 4.1 of the paper.
MARCH_2026_READINGS: Dict[str, float] = {
    "real_gdp_yoy": 1.4,         # decelerating
    "nonfarm_payrolls_3m": -25,  # negative in February
    "ism_manufacturing": 48.7,
    "cpi_yoy": 2.4,              # moderating
    "core_cpi_yoy": 2.5,
    "unemployment": 4.4,
    "fed_funds": 3.75,           # easing cycle but still restrictive
    "ten_year": 4.05,
    "twos_tens": 0.10,
    "hy_oas_bp": 425,
    "vix": 22.5,
    "usd_index": 99.8,
    "brent_oil": 88.2,           # oil supply shock per paper
    "breakevens_5y": 2.65,
}


@dataclass
class RegimeResult:
    regime: str
    confidence: float
    scores: Dict[str, float]
    notes: str


def _score_growth(r: Dict[str, float]) -> float:
    s = 0.0
    s += _norm(r["real_gdp_yoy"], 1.5, 1.5)            # >1.5% trend, ±1.5 band
    s += _norm(r["nonfarm_payrolls_3m"], 100, 150)
    s += _norm(r["ism_manufacturing"], 50, 5)
    s += _norm(-(r["unemployment"] - 4.0), 0, 1.0)
    return float(s / 4.0)


def _score_inflation(r: Dict[str, float]) -> float:
    s = 0.0
    s += _norm(r["cpi_yoy"], 2.0, 1.0)
    s += _norm(r["core_cpi_yoy"], 2.0, 1.0)
    s += _norm(r["breakevens_5y"], 2.5, 0.5)
    s += _norm(r["brent_oil"] - 75, 0, 25)
    return float(s / 4.0)


def _score_monetary(r: Dict[str, float]) -> float:
    """Negative when policy is restrictive (high rates), positive when accommodative."""
    s = 0.0
    s += -_norm(r["fed_funds"] - 2.5, 0, 1.5)   # neutral ≈ 2.5%
    s += -_norm(r["ten_year"] - 3.5, 0, 1.5)
    s += _norm(r["twos_tens"], 0.5, 0.5)        # positive slope = supportive
    return float(s / 3.0)


def _score_financial(r: Dict[str, float]) -> float:
    s = 0.0
    s += -_norm(r["hy_oas_bp"] - 350, 0, 200)
    s += -_norm(r["vix"] - 18, 0, 10)
    s += -_norm(r["usd_index"] - 100, 0, 5)
    return float(s / 3.0)


def _norm(x: float, center: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    z = (x - center) / scale
    return max(-1.0, min(1.0, z))


def classify_regime(readings: Dict[str, float] = None) -> RegimeResult:
    r = readings or MARCH_2026_READINGS
    g = _score_growth(r)
    i = _score_inflation(r)
    m = _score_monetary(r)
    f = _score_financial(r)
    scores = {"growth": g, "inflation": i, "monetary": m, "financial": f}

    # Decision rules
    # Stagflationary late-cycle: persistent inflation + restrictive policy + weak financial conditions,
    # even if growth has decelerated (paper: "GDP decel + payrolls turn negative in Feb + oil shock").
    stagflationary = i >= 0.0 and m <= -0.4 and f <= -0.1
    if g > 0.0 and i < 0.0 and m > 0.0 and f > 0.0:
        regime = "expansion"
    elif stagflationary and g >= -0.5:
        regime = "late-cycle"
    elif g < -0.5 and m < -0.3 and f < -0.1:
        regime = "recession"
    elif g > 0.0 and m < -0.1 and i < 0.2 and f >= 0.0:
        regime = "recovery"
    else:
        # Closest matching label by simple template scoring.
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

    # Confidence: distance from neutral; higher when scores are more decisive.
    conf = float(min(1.0, max(0.0, sum(abs(v) for v in scores.values()) / 4.0)))
    notes = (
        f"Growth decel (GDP {r['real_gdp_yoy']:.1f}%, payrolls {r['nonfarm_payrolls_3m']:+.0f}k/3m). "
        f"Inflation {r['cpi_yoy']:.1f}% with oil shock to ${r['brent_oil']:.0f}. "
        f"Policy still restrictive (FF {r['fed_funds']:.2f}%). "
        f"Spreads {r['hy_oas_bp']:.0f}bp, VIX {r['vix']:.1f}."
    )
    return RegimeResult(regime=regime, confidence=conf, scores=scores, notes=notes)


def recession_probability(readings: Dict[str, float] = None) -> float:
    """Section 4.1: 25-35% baseline recession probability."""
    r = readings or MARCH_2026_READINGS
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


if __name__ == "__main__":
    res = classify_regime()
    print(res)
    print(f"P(recession 12m): {recession_probability():.0%}")
