"""
Mock LLM (stub) used for offline runs.

Each agent in the paper "reasons in natural language" and emits structured outputs.
We faithfully *simulate* this behavior: every agent that would call an LLM instead
calls into a deterministic, rule-based judge that follows the heuristics described
in the paper (CMA Judge skill in Exhibit 4, voting protocol in Section 3.5,
ensemble selection in Section 3.6, etc.).

This is the *stub* layer. If a real Anthropic API key is available, the same
interface can be implemented by a real LLM client. The pipeline is unaware of
which is in use.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np


def _seed_from(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)


@dataclass
class LLMResponse:
    text: str
    structured: Dict[str, Any]


class StubLLM:
    """A deterministic stand-in for an LLM."""

    def __init__(self, name: str = "stub-llm-v1", seed: int = 42):
        self.name = name
        self.seed = seed

    # ------------------------------------------------------------------
    # CMA Judge (Exhibit 4)
    # ------------------------------------------------------------------
    def cma_judge(
        self,
        candidates: Dict[str, float],
        confidences: Dict[str, float],
        regime: str,
        valuation_pe: Optional[float],
        is_equity: bool,
        slug: str,
        curve_signal: Optional[Dict[str, Any]] = None,
        asset_profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Implements the CMA-judge skill rules:
          1) Assess dispersion (tight <3pp / moderate 3-6pp / wide >6pp)
          2) Apply regime logic
              late-cycle  -> tilt valuation + regime_adj
              expansion   -> auto_blend
              recession   -> regime_adj + BL
              recovery    -> historical_erp + auto_blend
          3) Check valuation context (PE >30 -> valuation; PE <12 -> historical+BL)
          4) Constraint: final must be within [min, max] of candidates.
        """
        names = list(candidates.keys())
        vals = np.array([candidates[k] for k in names])
        lo, hi = float(vals.min()), float(vals.max())
        spread_pp = (hi - lo) * 100.0
        dispersion = "tight" if spread_pp < 3 else ("moderate" if spread_pp < 6 else "wide")

        # Default = auto_blend
        weights: Dict[str, float] = {k: 0.0 for k in names}
        if "auto_blend" in weights:
            weights["auto_blend"] = 1.0

        rationale_parts: List[str] = [
            f"Dispersion {dispersion} ({spread_pp:.1f}pp).",
        ]

        if is_equity:
            # Regime logic
            if regime == "late-cycle":
                weights = self._mix(weights, {
                    "implied_erp": 0.30,
                    "inverse_gordon": 0.30,
                    "regime_adjusted": 0.25,
                    "auto_blend": 0.10,
                    "historical_erp": 0.05,
                })
                rationale_parts.append("Late-cycle: tilt to valuation + regime-adjusted.")
            elif regime == "expansion":
                weights = self._mix(weights, {"auto_blend": 1.0})
                rationale_parts.append("Expansion: confidence-weighted auto-blend dominates.")
            elif regime == "recession":
                weights = self._mix(weights, {
                    "regime_adjusted": 0.40,
                    "bl_equilibrium": 0.30,
                    "auto_blend": 0.20,
                    "implied_erp": 0.10,
                })
                rationale_parts.append("Recession: regime-adjusted + BL anchor.")
            elif regime == "recovery":
                weights = self._mix(weights, {
                    "historical_erp": 0.30,
                    "auto_blend": 0.40,
                    "regime_adjusted": 0.20,
                    "bl_equilibrium": 0.10,
                })
                rationale_parts.append("Recovery: historical ERP + auto-blend.")

            # Valuation override
            if valuation_pe is not None:
                if valuation_pe > 30:
                    weights = self._tilt(weights, "implied_erp", 0.20)
                    weights = self._tilt(weights, "inverse_gordon", 0.20)
                    weights = self._tilt(weights, "historical_erp", -0.30)
                    rationale_parts.append(f"PE {valuation_pe:.1f}>30: heavy valuation tilt.")
                elif valuation_pe < 12:
                    weights = self._tilt(weights, "historical_erp", 0.15)
                    weights = self._tilt(weights, "bl_equilibrium", 0.15)
                    rationale_parts.append(f"PE {valuation_pe:.1f}<12: historical + BL tilt.")
        else:
            # Fixed-income / real-asset path: lean on regime-adjusted + auto-blend.
            curve_regime = (curve_signal or {}).get("regime")
            if curve_regime and "curve_adjusted" in weights:
                weights = self._non_equity_curve_mix(curve_regime, asset_profile, names)
                rationale_parts.append(
                    f"Non-equity: curve state '{curve_regime}' applied to {asset_profile or 'generic'} profile."
                )
            elif regime in ("late-cycle", "recession"):
                weights = self._mix(weights, {
                    "regime_adjusted": 0.50,
                    "auto_blend": 0.40,
                    "yield_carry": 0.10,
                })
                rationale_parts.append("Non-equity: lean on yield/regime adjusted blend.")
            else:
                weights = self._mix(weights, {
                    "auto_blend": 0.70,
                    "yield_carry": 0.20,
                    "regime_adjusted": 0.10,
                })
                rationale_parts.append("Non-equity: lean on yield/regime adjusted blend.")

        # Re-normalize over candidates that exist.
        weights = {k: weights.get(k, 0.0) for k in names}
        s = sum(weights.values()) or 1.0
        weights = {k: v / s for k, v in weights.items()}

        # Final estimate.
        final = float(sum(weights[k] * candidates[k] for k in names))
        # Clip into [lo, hi].
        final = max(lo, min(hi, final))

        return {
            "final": final,
            "weights": weights,
            "dispersion": dispersion,
            "rationale": " ".join(rationale_parts),
        }

    @staticmethod
    def _mix(base: Dict[str, float], delta: Dict[str, float]) -> Dict[str, float]:
        out = {k: 0.0 for k in base}
        for k, v in delta.items():
            if k in out:
                out[k] = v
        return out

    @staticmethod
    def _tilt(weights: Dict[str, float], key: str, amount: float) -> Dict[str, float]:
        if key not in weights:
            return weights
        out = dict(weights)
        out[key] = max(0.0, out[key] + amount)
        # Re-normalize
        s = sum(out.values()) or 1.0
        return {k: v / s for k, v in out.items()}

    @staticmethod
    def _non_equity_curve_mix(
        curve_regime: str,
        asset_profile: Optional[str],
        method_names: List[str],
    ) -> Dict[str, float]:
        profile = asset_profile or "credit"
        if profile == "long_duration":
            if curve_regime.startswith("bear"):
                raw = {"curve_adjusted": 0.45, "yield_carry": 0.25, "auto_blend": 0.20, "regime_adjusted": 0.10}
            else:
                raw = {"curve_adjusted": 0.40, "regime_adjusted": 0.30, "auto_blend": 0.20, "yield_carry": 0.10}
        elif profile == "cash":
            if curve_regime.startswith("bear"):
                raw = {"curve_adjusted": 0.45, "yield_carry": 0.25, "auto_blend": 0.20, "regime_adjusted": 0.10}
            else:
                raw = {"yield_carry": 0.35, "auto_blend": 0.30, "curve_adjusted": 0.25, "regime_adjusted": 0.10}
        elif profile == "credit":
            if curve_regime.startswith("bear"):
                raw = {"curve_adjusted": 0.35, "auto_blend": 0.30, "yield_carry": 0.20, "regime_adjusted": 0.15}
            else:
                raw = {"curve_adjusted": 0.30, "regime_adjusted": 0.30, "auto_blend": 0.25, "yield_carry": 0.15}
        else:
            raw = {"curve_adjusted": 0.30, "auto_blend": 0.30, "regime_adjusted": 0.25, "yield_carry": 0.15}
        return {k: raw.get(k, 0.0) for k in method_names}

    # ------------------------------------------------------------------
    # Peer review narrative (Section 3.5)
    # ------------------------------------------------------------------
    def peer_review(
        self,
        reviewer_slug: str,
        target_slug: str,
        target_metrics: Dict[str, float],
        same_category: bool,
    ) -> Dict[str, Any]:
        # Heuristic score in [0, 1] from metrics.
        sharpe = target_metrics.get("backtest_sharpe", 0.0)
        ips_ok = float(target_metrics.get("ips_compliance", 1.0))
        diversification = float(target_metrics.get("diversification", 0.5))
        regime_fit = float(target_metrics.get("regime_fit", 0.5))
        est_robust = float(target_metrics.get("estimation_robustness", 0.5))
        cma_util = float(target_metrics.get("cma_utilization", 0.5))

        score = (
            0.25 * min(1.0, max(0.0, sharpe / 0.6))
            + 0.15 * ips_ok
            + 0.15 * diversification
            + 0.20 * regime_fit
            + 0.15 * est_robust
            + 0.10 * cma_util
        )

        # Same-category reviewers slightly more critical (technical errors).
        if same_category:
            score *= 0.96

        verdict = "approve" if score > 0.55 else ("revise" if score > 0.40 else "reject")
        comment = (
            f"{reviewer_slug} reviewing {target_slug} "
            f"({'same' if same_category else 'cross'}-category): "
            f"sharpe={sharpe:.2f}, regime_fit={regime_fit:.2f}, ips_ok={ips_ok:.2f}. "
            f"Verdict: {verdict}."
        )
        return {"score": float(score), "verdict": verdict, "comment": comment}

    # ------------------------------------------------------------------
    # CIO ensemble narrative (Section 3.6)
    # ------------------------------------------------------------------
    def cio_select_ensemble(
        self,
        regime: str,
        ensemble_diagnostics: Dict[str, Dict[str, float]],
        macro_readings: Dict[str, float] | None = None,
        recession_probability: float | None = None,
    ) -> Dict[str, Any]:
        """
        Given diagnostics for each ensemble method, pick one.
        Late-cycle / recession -> inverse-tracking-error weighting (paper's choice).
        Expansion -> backtest-Sharpe weighting.
        Recovery -> regime-conditional weighting.
        """
        preference: Dict[str, str] = {
            "late-cycle": "inverse_te",
            "recession": "trimmed_mean",
            "expansion": "backtest_sharpe",
            "recovery": "regime_conditional",
        }
        choice = preference.get(regime, "inverse_te")
        if choice not in ensemble_diagnostics:
            # Fall back to highest composite score.
            choice = max(
                ensemble_diagnostics.items(),
                key=lambda kv: kv[1].get("composite", 0.0),
            )[0]
        rationale = (
            f"Regime '{regime}' favors '{choice}'. "
            f"Diagnostics: { {k: round(v.get('composite', 0.0), 3) for k, v in ensemble_diagnostics.items()} }."
        )
        return {"choice": choice, "rationale": rationale}


# Singleton helper.
_DEFAULT: Optional[StubLLM] = None


def get_llm() -> StubLLM:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = StubLLM()
    return _DEFAULT
