"""
Portfolio Construction (PC) agents.

Section 3.4 — 21 agents:
  - 19 canonical methods that run in parallel
  - PC-Researcher (max-entropy proposal in March 2026 run) joins as #20
  - Adversarial Diversifier runs after the others (#21)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .base import AgentContext, AgentSpec, BaseAgent
from ..skills.pc_methods import pc_engine
from ..skills.pc_methods.pc_engine import (
    Constraints,
    DISPATCH,
    adversarial_diversifier,
    make_constraints,
)
from ..skills.risk_assessment.risk_metrics import (
    backtest_metrics,
    cma_utilization,
    concentration_metrics,
    diversification_score,
    estimation_robustness,
    ex_ante_var,
    ex_ante_vol,
    factor_tilts,
    ips_compliance,
    regime_fit,
)


@dataclass
class PCResult:
    slug: str
    name: str
    category: str
    method: str
    weights: np.ndarray
    expected_return: float
    expected_vol: float
    metrics: Dict[str, float]


class PCAgent(BaseAgent):
    """A single PC agent."""

    def __init__(
        self,
        ctx: AgentContext,
        spec_entry: dict,
        mu: np.ndarray,
        Sigma: np.ndarray,
        returns: pd.DataFrame,
        constraints: Constraints,
        asset_classes: List[dict],
        benchmark_w: Optional[np.ndarray] = None,
    ):
        self.entry = spec_entry
        self.mu = mu
        self.Sigma = Sigma
        self.returns = returns
        self.cons = constraints
        self.asset_classes = asset_classes
        self.benchmark_w = benchmark_w
        self.SPEC = AgentSpec(
            slug=f"pc::{spec_entry['slug']}",
            role=f"PC method: {spec_entry['name']}",
            skills=["pc_methods", "risk_assessment"],
        )
        super().__init__(ctx)

    def run(self, others: Optional[List[np.ndarray]] = None) -> PCResult:
        method = self.entry["method"]
        if method == "adversarial_diversifier":
            w = adversarial_diversifier(self.mu, self.Sigma, self.returns, self.cons,
                                        others=others or [])
        else:
            fn = DISPATCH[method]
            w = fn(self.mu, self.Sigma, self.returns, self.cons)

        e_ret = float(w @ self.mu)
        e_vol = ex_ante_vol(w, self.Sigma)
        metrics = self._diagnose(w, method)

        # Persist
        weights_dict = {ac["slug"]: float(w[i]) for i, ac in enumerate(self.asset_classes)}
        payload = {
            "slug": self.entry["slug"],
            "name": self.entry["name"],
            "category": self.entry["category"],
            "method": method,
            "weights": weights_dict,
            "expected_return": e_ret,
            "expected_vol": e_vol,
            "metrics": metrics,
        }
        self.ctx.save_json(f"pc/{self.entry['slug']}/proposal.json", payload)
        self.ctx.save_md(f"pc/{self.entry['slug']}/proposal.md", self._render_md(payload))
        self.log(f"{self.entry['name']}: E[r]={e_ret:.2%} σ={e_vol:.2%} "
                 f"DivScore={metrics['diversification']:.2f}")
        return PCResult(
            slug=self.entry["slug"],
            name=self.entry["name"],
            category=self.entry["category"],
            method=method,
            weights=w,
            expected_return=e_ret,
            expected_vol=e_vol,
            metrics=metrics,
        )

    # ------------------------------------------------------------------
    def _diagnose(self, w: np.ndarray, method: str) -> Dict[str, float]:
        bt = backtest_metrics(w, self.returns)
        ips = self.ctx.config.get("ips", {})
        comp = ips_compliance(w, self.asset_classes, self.Sigma, self.benchmark_w, ips)
        regime = self.ctx.artifacts["macro_view"]["regime"]
        return {
            "ex_ante_vol": ex_ante_vol(w, self.Sigma),
            "ex_ante_var95": ex_ante_var(w, self.mu, self.Sigma, 0.95),
            "backtest_sharpe": bt["backtest_sharpe"],
            "backtest_vol": bt["backtest_vol"],
            "backtest_maxdd": bt["backtest_maxdd"],
            **concentration_metrics(w),
            "ips_compliance": comp["compliance_score"],
            "ips_flags": comp["flags"],
            "tracking_error": comp.get("tracking_error"),
            "factor_tilts": factor_tilts(w, self.asset_classes),
            "diversification": diversification_score(w, self.Sigma),
            "regime_fit": regime_fit(method, regime),
            "estimation_robustness": estimation_robustness(method, regime),
            "cma_utilization": cma_utilization(w, self.mu),
        }

    # ------------------------------------------------------------------
    def _render_md(self, p: Dict[str, Any]) -> str:
        m = p["metrics"]
        lines = [
            f"# PC Proposal — {p['name']}",
            "",
            f"**Category:** {p['category']}  ",
            f"**Method:** `{p['method']}`",
            "",
            "## Top Weights",
            "",
            "| Asset class | Weight |",
            "|-------------|--------|",
        ]
        for k, v in sorted(p["weights"].items(), key=lambda kv: kv[1], reverse=True)[:8]:
            lines.append(f"| {k} | {v:.1%} |")
        lines += [
            "",
            "## Diagnostics",
            "",
            f"- E[r]: {p['expected_return']:.2%}, σ: {p['expected_vol']:.2%}",
            f"- Backtest Sharpe: {m['backtest_sharpe']:.2f}, MaxDD: {m['backtest_maxdd']:.1%}",
            f"- Effective N: {m['effective_n']:.1f}, Top-3 weight: {m['top3']:.0%}",
            f"- IPS compliance: {m['ips_compliance']:.2f} (flags: {len(m['ips_flags'])})",
            f"- Diversification score: {m['diversification']:.2f}",
            f"- Regime fit: {m['regime_fit']:.2f}",
            f"- Estimation robustness: {m['estimation_robustness']:.2f}",
            f"- CMA utilization: {m['cma_utilization']:+.2f}",
        ]
        return "\n".join(lines)


class PCResearcherAgent(BaseAgent):
    """
    Researcher agent (Section 3.4): proposes a new portfolio construction method
    not yet represented in the registry. In the March 2026 run, the proposal is
    the maximum-entropy portfolio (Bera-Park 2008).
    """
    SPEC = AgentSpec(
        slug="pc-researcher",
        role="Proposes a novel portfolio-construction method.",
        skills=["pc_methods"],
    )

    def __init__(self, ctx: AgentContext):
        super().__init__(ctx)

    def run(self) -> Dict[str, Any]:
        proposal = {
            "proposed_method": "max_entropy",
            "name": "Maximum Entropy",
            "rationale": (
                "Maximizes Shannon entropy of portfolio weights subject to a Sharpe-ratio floor. "
                "Spans the gap between heuristic (1/N) and optimization-based methods, providing "
                "stability when expected returns are weakly identified (Bera & Park 2008)."
            ),
            "constraints": ["sum(w) = 1", "w >= 0", "Sharpe >= 0.30"],
            "literature": [
                "Bera, A.K. and Park, S.Y. (2008) 'Optimal Portfolio Diversification Using the Maximum "
                "Entropy Principle.' Econometric Reviews."
            ],
        }
        self.ctx.save_json("pc/_researcher_proposal.json", proposal)
        self.ctx.save_md(
            "pc/_researcher_proposal.md",
            f"# PC-Researcher Proposal\n\n"
            f"Method: **{proposal['name']}**\n\n{proposal['rationale']}\n",
        )
        self.log("Proposed Maximum Entropy method.")
        return proposal
