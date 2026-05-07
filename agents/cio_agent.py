"""
CIO Agent.

Section 3.6: scores all PC methods on six dimensions, evaluates 7 ensemble
combinations, picks one (LLM-as-judge), and writes the final allocation +
board memo.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .base import AgentContext, AgentSpec, BaseAgent
from ..llm.stub_llm import get_llm
from ..skills.ensemble_combination.ensembles import METHODS as ENSEMBLE_METHODS
from ..skills.risk_assessment.risk_metrics import (
    backtest_metrics,
    concentration_metrics,
    diversification_score,
    ex_ante_vol,
    ips_compliance,
)


_FI_CURVE_TILT: Dict[str, Dict[str, float]] = {
    "bear-parallel":   {"long_duration": 0.75, "credit": 0.95, "cash_like": 1.25},
    "bear-flattening": {"long_duration": 0.85, "credit": 0.95, "cash_like": 1.15},
    "bear-steepening": {"long_duration": 0.70, "credit": 0.95, "cash_like": 1.30},
    "bull-parallel":   {"long_duration": 1.25, "credit": 1.05, "cash_like": 0.75},
    "bull-flattening": {"long_duration": 1.30, "credit": 1.05, "cash_like": 0.75},
    "bull-steepening": {"long_duration": 1.15, "credit": 1.05, "cash_like": 0.85},
    "range-bound":     {"long_duration": 1.00, "credit": 1.00, "cash_like": 1.00},
    "static-parallel": {"long_duration": 1.00, "credit": 1.00, "cash_like": 1.00},
}

_LONG_DURATION_FI = {"kr-treasuries-10y", "us-treasuries-10y", "us-treasuries-30y"}
_CASH_LIKE_FI = {"kr-short-bonds"}


def _fi_profile(slug: str) -> str:
    if slug in _LONG_DURATION_FI:
        return "long_duration"
    if slug in _CASH_LIKE_FI:
        return "cash_like"
    return "credit"


class CIOAgent(BaseAgent):
    SPEC = AgentSpec(
        slug="cio-agent",
        role="Scores PC proposals; selects ensemble; produces board memo.",
        skills=["ensemble_combination", "risk_assessment"],
    )

    def run(
        self,
        pc_results: List[Any],
        Sigma: np.ndarray,
        mu: np.ndarray,
        returns: pd.DataFrame,
        asset_classes: List[Dict[str, Any]],
        review_payload: Dict[str, Any],
        ips: Dict[str, Any],
        benchmark_w: np.ndarray,
    ) -> Dict[str, Any]:
        weights = {r.slug: r.weights for r in pc_results}
        sharpes = {r.slug: r.metrics.get("backtest_sharpe", 0.0) for r in pc_results}
        scores = review_payload["composite"]

        # Build the 7 ensemble candidates.
        ens: Dict[str, np.ndarray] = {}
        ens["simple_average"]     = ENSEMBLE_METHODS["simple_average"](weights)
        ens["inverse_te"]         = ENSEMBLE_METHODS["inverse_te"](weights, Sigma)
        ens["backtest_sharpe"]    = ENSEMBLE_METHODS["backtest_sharpe"](weights, sharpes)
        ens["meta_optimization"]  = ENSEMBLE_METHODS["meta_optimization"](weights, Sigma, returns)
        ens["regime_conditional"] = ENSEMBLE_METHODS["regime_conditional"](weights, self.ctx.artifacts["macro_view"]["regime"])
        ens["composite_score"]    = ENSEMBLE_METHODS["composite_score"](weights, scores)
        ens["trimmed_mean"]       = ENSEMBLE_METHODS["trimmed_mean"](weights, scores)

        # Score each ensemble via the same diagnostic suite.
        diagnostics: Dict[str, Dict[str, float]] = {}
        for name, w in ens.items():
            wn = self._normalize_to_constraints(w, asset_classes, ips)
            ens[name] = wn
            diagnostics[name] = self._score_portfolio(wn, mu, Sigma, returns, asset_classes, ips, benchmark_w)

        # CIO LLM-as-judge picks an ensemble.
        mv = self.ctx.artifacts["macro_view"]
        regime = mv["regime"]
        choice = get_llm().cio_select_ensemble(
            regime, diagnostics,
            macro_readings=mv.get("readings"),
            recession_probability=mv.get("recession_probability_12m"),
        )
        chosen_name = choice["choice"]
        chosen_w_raw = ens[chosen_name]

        # Curve-driven FI-internal tilt — preserves FI sum and other category sums.
        chosen_w, tilt_info = self._apply_fi_curve_tilt(
            chosen_w_raw, asset_classes, mv.get("curve_signal")
        )

        # Compute ensemble PC weights (how much weight each PC contributes to the chosen).
        # For 'inverse_te' specifically we expose the underlying agent weights.
        agent_weights = self._inverse_te_agent_weights(weights, Sigma) if chosen_name == "inverse_te" else \
                        self._derive_agent_weights(weights, chosen_w_raw)

        # Final metrics recomputed on tilted weights so dashboard numbers reflect what's shown.
        final_metrics = self._score_portfolio(chosen_w, mu, Sigma, returns, asset_classes, ips, benchmark_w)
        final = {
            "chosen_ensemble": chosen_name,
            "rationale": choice["rationale"],
            "weights": {ac["slug"]: float(chosen_w[i]) for i, ac in enumerate(asset_classes)},
            "weights_pre_tilt": {ac["slug"]: float(chosen_w_raw[i]) for i, ac in enumerate(asset_classes)},
            "fi_curve_tilt": tilt_info,
            "ensemble_agent_weights": {k: float(v) for k, v in agent_weights.items()},
            "metrics": final_metrics,
            "ensembles": {name: {ac["slug"]: float(w[i]) for i, ac in enumerate(asset_classes)}
                          for name, w in ens.items()},
            "diagnostics": diagnostics,
        }
        self.ctx.save_json("cio/final_portfolio.json", final)

        # Board memo
        board_memo = self._board_memo(final, mu, Sigma, returns, asset_classes, ips, benchmark_w, review_payload)
        self.ctx.save_md("cio/board_memo.md", board_memo)
        self.log(f"Selected '{chosen_name}': E[r]={final_metrics['expected_return']:.2%}, "
                 f"σ={final_metrics['expected_vol']:.2%}, TE={final_metrics.get('tracking_error', 0) or 0:.2%}")
        self.ctx.artifacts["cio_final"] = final
        return final

    # ------------------------------------------------------------------
    def _apply_fi_curve_tilt(
        self,
        w: np.ndarray,
        asset_classes: List[Dict[str, Any]],
        curve_signal: Optional[Dict[str, Any]],
    ):
        info: Dict[str, Any] = {"applied": False, "regime": None, "rules": None,
                                "fi_total": None, "shifts_pp": {}}
        if not curve_signal:
            return np.asarray(w, dtype=float).copy(), info
        regime = curve_signal.get("regime", "range-bound")
        rules = _FI_CURVE_TILT.get(regime)
        if rules is None:
            info["regime"] = regime
            return np.asarray(w, dtype=float).copy(), info

        fi_idx = [i for i, ac in enumerate(asset_classes) if ac["category"] == "FixedIncome"]
        if not fi_idx:
            info["regime"] = regime
            return np.asarray(w, dtype=float).copy(), info

        w_old = np.asarray(w, dtype=float)
        fi_total = float(w_old[fi_idx].sum())
        if fi_total <= 1e-9:
            info["regime"] = regime
            return w_old.copy(), info

        w_new = w_old.copy()
        for i in fi_idx:
            slug = asset_classes[i]["slug"]
            w_new[i] = w_old[i] * rules.get(_fi_profile(slug), 1.0)
        new_fi_total = float(w_new[fi_idx].sum())
        if new_fi_total <= 1e-9:
            info["regime"] = regime
            return w_old.copy(), info
        scale = fi_total / new_fi_total
        for i in fi_idx:
            w_new[i] *= scale

        shifts_pp = {asset_classes[i]["slug"]: float((w_new[i] - w_old[i]) * 100.0) for i in fi_idx}
        info.update({
            "applied": True,
            "regime": regime,
            "rules": rules,
            "fi_total": fi_total,
            "shifts_pp": shifts_pp,
        })
        self.log(
            f"FI curve tilt '{regime}' applied (FI total preserved at {fi_total*100:.1f}%); "
            f"shifts(pp): " + ", ".join(f"{k}{v:+.2f}" for k, v in shifts_pp.items())
        )
        return w_new, info

    def _score_portfolio(self, w, mu, Sigma, returns, asset_classes, ips, benchmark_w):
        bt = backtest_metrics(w, returns)
        comp = ips_compliance(w, asset_classes, Sigma, benchmark_w, ips)
        return {
            "expected_return": float(w @ mu),
            "expected_vol": ex_ante_vol(w, Sigma),
            "backtest_sharpe": bt["backtest_sharpe"],
            "backtest_maxdd": bt["backtest_maxdd"],
            **concentration_metrics(w),
            "ips_compliance": comp["compliance_score"],
            "tracking_error": comp.get("tracking_error"),
            "diversification": diversification_score(w, Sigma),
            "composite": (
                0.25 * min(1.0, max(0.0, bt["backtest_sharpe"] / 0.6))
                + 0.20 * comp["compliance_score"]
                + 0.20 * diversification_score(w, Sigma)
                + 0.15 * (1.0 - min(1.0, abs((comp.get("tracking_error") or 0) / 0.06)))
                + 0.20 * (1.0 - min(1.0, abs(bt["backtest_maxdd"]) / 0.40))
            ),
        }

    def _normalize_to_constraints(self, w, asset_classes, ips):
        from ..skills.pc_methods.pc_engine import _project_to_constraints, make_constraints
        cb = ips.get("constraints", {}).get("category_bounds", {})
        cat_min = {k: v.get("min", 0.0) for k, v in cb.items()}
        cat_max = {k: v.get("max", 1.0) for k, v in cb.items()}
        pos = ips.get("constraints", {}).get("position_limits", {})
        cons = make_constraints(asset_classes,
                                pos_min=pos.get("min", 0.0),
                                pos_max=pos.get("max", 1.0),
                                cat_min=cat_min, cat_max=cat_max)
        return _project_to_constraints(np.asarray(w, dtype=float), cons)

    def _inverse_te_agent_weights(self, weights, Sigma):
        keys = list(weights.keys())
        W = np.vstack([weights[k] for k in keys])
        centroid = W.mean(axis=0)
        tes = np.array([np.sqrt(max((W[i] - centroid) @ Sigma @ (W[i] - centroid), 1e-12))
                        for i in range(W.shape[0])])
        inv = 1.0 / np.maximum(tes, 1e-9)
        inv = inv / inv.sum()
        return dict(zip(keys, inv))

    def _derive_agent_weights(self, weights, chosen_w):
        # Solve a non-negative least squares: chosen_w ≈ Σ a_i w_i.
        keys = list(weights.keys())
        W = np.vstack([weights[k] for k in keys]).T  # N x K
        # quick lstsq + clip
        a, _, _, _ = np.linalg.lstsq(W, chosen_w, rcond=None)
        a = np.maximum(a, 0)
        if a.sum() <= 0:
            a = np.ones(len(keys))
        a = a / a.sum()
        return dict(zip(keys, a))

    # ------------------------------------------------------------------
    def _board_memo(self, final, mu, Sigma, returns, asset_classes, ips, benchmark_w, review):
        m = final["metrics"]
        regime = self.ctx.artifacts["macro_view"]["regime"]
        bench_metrics = backtest_metrics(benchmark_w, returns)
        wsorted = sorted(final["weights"].items(), key=lambda kv: kv[1], reverse=True)
        top5 = wsorted[:5]
        agent_w = sorted(final["ensemble_agent_weights"].items(), key=lambda kv: kv[1], reverse=True)

        lines = [
            "# Board Memo — Strategic Asset Allocation",
            "",
            f"_Date: {pd.Timestamp.today():%Y-%m-%d}  |  Pipeline: agentic SAA (offline run)_",
            "",
            "## Recommendation",
            "",
            f"The CIO recommends an allocation produced by the **{final['chosen_ensemble']}** "
            f"ensemble across {len(final['ensemble_agent_weights'])} portfolio construction agents. "
            f"Selection rationale: {final['rationale']}",
            "",
            f"- Expected return (3y, nominal): **{m['expected_return']:.2%}**",
            f"- Expected volatility: **{m['expected_vol']:.2%}**",
            f"- Tracking error vs 60/40: **{(m.get('tracking_error') or 0):.2%}** "
            f"(budget {ips['active_risk_budget']['max_tracking_error']:.0%})",
            f"- Backtest Sharpe: **{m['backtest_sharpe']:.2f}** "
            f"(60/40 benchmark: {bench_metrics['backtest_sharpe']:.2f})",
            f"- Backtest max drawdown: **{m['backtest_maxdd']:.1%}** "
            f"(60/40 benchmark: {bench_metrics['backtest_maxdd']:.1%})",
            f"- Effective N (Meucci 2009): **{m['effective_n']:.1f}**",
            "",
            "## Macro Rationale",
            "",
            f"The macro-agent classifies the environment as **{regime}** with confidence "
            f"{self.ctx.artifacts['macro_view']['confidence']:.2f} and a 12m recession probability "
            f"of {self.ctx.artifacts['macro_view']['recession_probability_12m']:.0%}. "
            f"Notes: {self.ctx.artifacts['macro_view']['notes']}",
            "",
            "## Largest Positions",
            "",
            "| Asset class | Weight |",
            "|-------------|-------:|",
        ]
        for slug, w in top5:
            lines.append(f"| {slug} | {w:.2%} |")
        lines += [
            "",
            "## Top Contributing PC Agents",
            "",
            "| PC Agent | Ensemble weight |",
            "|----------|----------------:|",
        ]
        for slug, w in agent_w[:8]:
            lines.append(f"| {slug} | {w:.2%} |")

        # FI curve tilt narrative
        tilt = final.get("fi_curve_tilt") or {}
        if tilt.get("applied"):
            lines += [
                "",
                "## Yield-Curve FI Reallocation",
                "",
                f"- Curve regime: **{tilt['regime']}**",
                f"- FI category total preserved at **{tilt['fi_total']*100:.2f}%** "
                f"(equity / cash / real-asset weights unchanged from optimizer output)",
                "",
                "| FI ETF | Pre-tilt | Post-tilt | Δ (pp) |",
                "|--------|---------:|----------:|-------:|",
            ]
            for slug, dpp in sorted(tilt["shifts_pp"].items(), key=lambda kv: kv[1]):
                pre = final["weights_pre_tilt"][slug] * 100
                post = final["weights"][slug] * 100
                lines.append(f"| {slug} | {pre:.2f}% | {post:.2f}% | {dpp:+.2f} |")

        # IPS compliance snippet
        comp = ips_compliance(np.array([final['weights'][ac['slug']] for ac in asset_classes]),
                              asset_classes, Sigma, benchmark_w, ips)
        comp_str = "All IPS bounds satisfied." if not comp["flags"] else \
                   "IPS flags: " + "; ".join(comp["flags"])
        lines += [
            "",
            "## Key Risks to Monitor",
            "",
            "- Stagflationary risk: oil supply shock + sticky core inflation could re-accelerate CPI.",
            "- Concentration in international developed equity (~16% target) — FX risk.",
            "- Long-duration Treasury exposure if inflation surprises above forecast.",
            "",
            "## Rebalancing & Drift Triggers",
            "",
            f"- Frequency: {ips['constraints']['rebalancing']['frequency']}",
            f"- Drift trigger: {ips['constraints']['rebalancing']['drift_trigger']:.0%}",
            "- Off-cycle rebalance if any equity-vs-fixed-income drift exceeds 5% absolute.",
            "",
            "## IPS Compliance",
            "",
            comp_str,
            "",
            "## Dissent / Adversarial View",
            "",
        ]
        # Bottom-ranked methods from review = dissent.
        rank = review.get("rank", [])
        bottom = rank[-3:] if len(rank) >= 3 else rank
        if bottom:
            lines.append(
                f"The strategy review's lowest-ranked methods were: "
                f"{', '.join(bottom)}. The Adversarial Diversifier in particular receives nonzero "
                f"weight in the ensemble despite peer rejection because boosting-style ensemble "
                f"diversification benefits from orthogonal forecasters (Schapire 1990)."
            )
        return "\n".join(lines)
