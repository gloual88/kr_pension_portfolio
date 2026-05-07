"""
Capital Market Assumption (CMA) candidate methods.

Implements the seven equity methods (Section 3.3) and a parallel five-method set
for fixed-income / real-asset asset classes. Each method returns (estimate,
confidence in [0,1], component breakdown, one-line rationale).

Returns are nominal expected returns over a 3-year horizon, expressed as decimals.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class MethodResult:
    estimate: float
    confidence: float
    components: Dict[str, float]
    rationale: str


# ---------------------------------------------------------------------------
# Equity (S&P-style) seven methods
# ---------------------------------------------------------------------------
def historical_erp(realized_premium: float, rf: float) -> MethodResult:
    est = realized_premium + rf
    return MethodResult(
        est, 0.55,
        {"erp": realized_premium, "rf": rf},
        "Long-run realized equity premium added to current Rf.",
    )


def regime_adjusted(historical_premium: float, regime: str, rf: float) -> MethodResult:
    adj = {
        "expansion":  +0.005,
        "late-cycle": -0.020,
        "recession":  -0.030,
        "recovery":   +0.030,
    }.get(regime, 0.0)
    est = historical_premium + adj + rf
    return MethodResult(
        est, 0.65,
        {"historical": historical_premium, "regime_adj": adj, "rf": rf},
        f"Regime '{regime}' applies {adj:+.2%} adjustment to historical ERP.",
    )


def bl_equilibrium(market_cap_weight: float, cov_diag: float, lam: float, rf: float) -> MethodResult:
    """Reverse-optimization: implied μ = λ·Σw + rf approximated via own variance."""
    est = lam * cov_diag * market_cap_weight + rf
    return MethodResult(
        est, 0.55,
        {"lambda": lam, "var": cov_diag, "w_mkt": market_cap_weight, "rf": rf},
        "Black-Litterman equilibrium return implied by market-cap weights.",
    )


def inverse_gordon(div_yield: float, earn_growth: float, valuation_change: float) -> MethodResult:
    est = div_yield + earn_growth + valuation_change
    return MethodResult(
        est, 0.50,
        {"dy": div_yield, "g": earn_growth, "Δv": valuation_change},
        "Grinold-Kroner: dividend yield + earnings growth + valuation change.",
    )


def implied_erp_cape(cape: float, rf: float) -> MethodResult:
    """Earnings yield from CAPE as proxy for forward return."""
    earn_yield = 1.0 / max(cape, 1.0)
    est = earn_yield  # treat as nominal forward return
    conf = 0.55 if cape and cape > 0 else 0.30
    return MethodResult(
        est, conf,
        {"cape": cape, "earn_yield": earn_yield, "rf": rf},
        f"CAPE {cape:.1f} earnings yield {earn_yield:.2%} implied forward return.",
    )


def survey_analyst(consensus: float) -> MethodResult:
    return MethodResult(
        consensus, 0.45,
        {"consensus": consensus},
        "Consensus survey of analysts / macro view.",
    )


def auto_blend(methods: Dict[str, MethodResult]) -> MethodResult:
    if not methods:
        return MethodResult(0.0, 0.0, {}, "No methods supplied.")
    total = sum(m.confidence for m in methods.values()) or 1.0
    est = sum(m.estimate * m.confidence for m in methods.values()) / total
    return MethodResult(
        est, 0.70,
        {k: m.confidence for k, m in methods.items()},
        "Confidence-weighted blend of all candidate methods.",
    )


# ---------------------------------------------------------------------------
# Fixed Income / Real Assets parallel methods
# ---------------------------------------------------------------------------
def yield_carry(yield_to_worst: float) -> MethodResult:
    return MethodResult(
        yield_to_worst, 0.65,
        {"ytw": yield_to_worst},
        "Yield-to-worst as forward-return anchor.",
    )


def rolldown_enhanced(yield_to_worst: float, rolldown: float) -> MethodResult:
    est = yield_to_worst + rolldown
    return MethodResult(est, 0.55, {"ytw": yield_to_worst, "roll": rolldown},
                        "Yield + roll-down on the curve.")


def term_premium_adj(yield_to_worst: float, term_premium: float) -> MethodResult:
    est = yield_to_worst + term_premium
    return MethodResult(est, 0.50, {"ytw": yield_to_worst, "tp": term_premium},
                        "Yield adjusted for current term premium estimate.")


def regime_adjusted_fi(historical_return: float, regime: str) -> MethodResult:
    adj = {
        "expansion":  -0.010,
        "late-cycle": +0.005,
        "recession":  +0.020,
        "recovery":   -0.005,
    }.get(regime, 0.0)
    est = historical_return + adj
    return MethodResult(est, 0.60, {"hist": historical_return, "adj": adj},
                        f"Regime '{regime}' adjustment to historical return.")


def curve_regime_adjusted_fi(
    yield_to_worst: float,
    historical_return: float,
    curve_signal: Dict[str, Any],
    asset_profile: str,
) -> MethodResult:
    curve_regime = curve_signal.get("regime", "range-bound")
    curve_shape = curve_signal.get("shape", "normal")
    base = 0.5 * yield_to_worst + 0.5 * historical_return

    move_adj = {
        "long_duration": {
            "bear-flattening": -0.015,
            "bear-steepening": -0.010,
            "bear-parallel": -0.008,
            "bull-flattening": 0.010,
            "bull-steepening": 0.015,
            "bull-parallel": 0.008,
        },
        "credit": {
            "bear-flattening": -0.006,
            "bear-steepening": -0.010,
            "bear-parallel": -0.004,
            "bull-flattening": 0.003,
            "bull-steepening": 0.004,
            "bull-parallel": 0.002,
        },
        "cash": {
            "bear-flattening": 0.005,
            "bear-steepening": 0.004,
            "bear-parallel": 0.003,
            "bull-flattening": -0.002,
            "bull-steepening": -0.003,
            "bull-parallel": -0.001,
        },
        "real_asset": {
            "bear-flattening": 0.002,
            "bear-steepening": 0.003,
            "bull-flattening": 0.001,
            "bull-steepening": -0.001,
        },
    }
    shape_adj = {
        "long_duration": {"inverted": -0.004, "flat": -0.002, "steep": 0.002},
        "credit": {"inverted": -0.002, "flat": -0.001},
        "cash": {"inverted": 0.002, "flat": 0.001, "steep": -0.001},
        "real_asset": {"inverted": 0.001},
    }

    profile = asset_profile if asset_profile in move_adj else "real_asset"
    adj = move_adj.get(profile, {}).get(curve_regime, 0.0)
    adj += shape_adj.get(profile, {}).get(curve_shape, 0.0)
    est = base + adj
    confidence = 0.65 if curve_regime not in ("range-bound", "static-parallel") else 0.50
    return MethodResult(
        est,
        confidence,
        {"base": base, "curve_adj": adj},
        f"Curve state '{curve_regime}' ({curve_shape}) applied to {asset_profile} profile.",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def collect_candidates_equity(
    historical_premium: float,
    rf: float,
    regime: str,
    market_cap_weight: float,
    cov_diag: float,
    lam: float,
    div_yield: float,
    earn_growth: float,
    valuation_change: float,
    cape: float,
    consensus: float,
) -> Dict[str, MethodResult]:
    methods: Dict[str, MethodResult] = {}
    methods["historical_erp"] = historical_erp(historical_premium, rf)
    methods["regime_adjusted"] = regime_adjusted(historical_premium, regime, rf)
    methods["bl_equilibrium"] = bl_equilibrium(market_cap_weight, cov_diag, lam, rf)
    methods["inverse_gordon"] = inverse_gordon(div_yield, earn_growth, valuation_change)
    methods["implied_erp"] = implied_erp_cape(cape, rf)
    methods["survey_analyst"] = survey_analyst(consensus)
    methods["auto_blend"] = auto_blend({k: v for k, v in methods.items()})
    return methods


def collect_candidates_fi(
    yield_to_worst: float,
    rolldown: float,
    term_premium: float,
    historical_return: float,
    regime: str,
    curve_signal: Optional[Dict[str, Any]] = None,
    asset_profile: str = "credit",
) -> Dict[str, MethodResult]:
    methods: Dict[str, MethodResult] = {}
    methods["yield_carry"] = yield_carry(yield_to_worst)
    methods["rolldown_enhanced"] = rolldown_enhanced(yield_to_worst, rolldown)
    methods["term_premium_adj"] = term_premium_adj(yield_to_worst, term_premium)
    methods["regime_adjusted"] = regime_adjusted_fi(historical_return, regime)
    if curve_signal:
        methods["curve_adjusted"] = curve_regime_adjusted_fi(
            yield_to_worst, historical_return, curve_signal, asset_profile
        )
    methods["auto_blend"] = auto_blend({k: v for k, v in methods.items()})
    return methods


def to_jsonable(methods: Dict[str, MethodResult]) -> Dict[str, dict]:
    return {
        k: {
            "estimate": float(v.estimate),
            "confidence": float(v.confidence),
            "components": {ck: float(cv) for ck, cv in v.components.items()},
            "rationale": v.rationale,
        }
        for k, v in methods.items()
    }
