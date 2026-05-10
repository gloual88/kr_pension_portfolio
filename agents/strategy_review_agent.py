"""
Strategy Review Agent.

Implements Section 3.5: peer review (each PC reviews 2 peers, 1 same-category +
1 cross-category) followed by Borda-count voting (top-5 pts 5,4,3,2,1; bottom -2).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from .base import AgentContext, AgentSpec, BaseAgent
from ..llm.stub_llm import get_llm
from ..skills.strategy_review.voting import (
    Ballot,
    assign_review_targets,
    tally,
)


def _composite_metric(metrics: Dict[str, float]) -> float:
    """Weighted composite: sharpe(25) + ips(15) + div(15) + regime(20) + est(15) + cma(10).

    Sharpe denominator widened 0.6 → 1.2 (parity with cio_agent._score_portfolio) so that
    high-Sharpe PC methods are differentiated in peer voting instead of saturating at 1.0.
    """
    sh = max(0.0, min(1.0, metrics.get("backtest_sharpe", 0.0) / 1.2))
    ips = float(metrics.get("ips_compliance", 1.0))
    div = float(metrics.get("diversification", 0.5))
    reg = float(metrics.get("regime_fit", 0.5))
    est = float(metrics.get("estimation_robustness", 0.5))
    cma = float(max(0.0, min(1.0, 0.5 + 0.5 * metrics.get("cma_utilization", 0.0))))
    return 0.25 * sh + 0.15 * ips + 0.15 * div + 0.20 * reg + 0.15 * est + 0.10 * cma


class StrategyReviewAgent(BaseAgent):
    SPEC = AgentSpec(
        slug="strategy-review",
        role="Peer review + Borda count voting orchestrator.",
        skills=["strategy_review"],
    )

    def __init__(self, ctx: AgentContext, seed: int = 2026):
        super().__init__(ctx)
        self.seed = seed

    def run(self, pc_results: List[Any]) -> Dict[str, Any]:
        candidates = [{"slug": r.slug, "name": r.name, "category": r.category} for r in pc_results]
        meta = {c["slug"]: c["category"] for c in candidates}
        results_by_slug = {r.slug: r for r in pc_results}

        # Stage 1: Assign reviewers
        assignments = assign_review_targets(candidates, seed=self.seed)
        review_records: Dict[str, List[Dict[str, Any]]] = {c["slug"]: [] for c in candidates}

        # Stage 2: Each PC writes 2 reviews
        for reviewer_slug, targets in assignments.items():
            for tgt_slug, same_cat in targets:
                tgt = results_by_slug[tgt_slug]
                review = get_llm().peer_review(
                    reviewer_slug=reviewer_slug,
                    target_slug=tgt_slug,
                    target_metrics={
                        "backtest_sharpe": tgt.metrics.get("backtest_sharpe", 0.0),
                        "ips_compliance": tgt.metrics.get("ips_compliance", 1.0),
                        "diversification": tgt.metrics.get("diversification", 0.5),
                        "regime_fit": tgt.metrics.get("regime_fit", 0.5),
                        "estimation_robustness": tgt.metrics.get("estimation_robustness", 0.5),
                        "cma_utilization": (1 + tgt.metrics.get("cma_utilization", 0.0)) / 2,
                    },
                    same_category=same_cat,
                )
                review["reviewer"] = reviewer_slug
                review["target"] = tgt_slug
                review["same_category"] = same_cat
                review_records[tgt_slug].append(review)

        # Stage 3: Each PC casts a ballot — top-5 + bottom flag (excluding self)
        ballots: List[Ballot] = []
        rng = random.Random(self.seed)
        # Score each peer from a reviewer's perspective using its own composite.
        for voter in candidates:
            others = [c for c in candidates if c["slug"] != voter["slug"]]
            scored = sorted(
                others,
                key=lambda c: _composite_metric(results_by_slug[c["slug"]].metrics) +
                              0.04 * rng.uniform(-1, 1),  # small jitter for individual prior
                reverse=True,
            )
            top5 = [c["slug"] for c in scored[:5]]
            bottom = scored[-1]["slug"]
            ballots.append(Ballot(voter=voter["slug"], top5=top5, bottom=bottom))

        # Stage 4: Tally with composite metric per slug.
        metric_scores = {r.slug: _composite_metric(r.metrics) for r in pc_results}
        regime = self.ctx.artifacts["macro_view"]["regime"]
        result = tally(ballots, metric_scores, meta, regime)

        # Persist
        review_payload = {
            "assignments": {k: v for k, v in assignments.items()},
            "reviews": review_records,
            "ballots": [{"voter": b.voter, "top5": b.top5, "bottom": b.bottom} for b in ballots],
            "vote_points": result.points,
            "metric_scores": metric_scores,
            "composite": result.composite,
            "rank": result.rank,
        }
        self.ctx.save_json("reviews/strategy_review.json", review_payload)
        self.ctx.save_md("reviews/strategy_review.md", self._render_md(review_payload, candidates))

        self.log(f"Top-5: {', '.join(result.rank[:5])}")
        self.ctx.artifacts["strategy_review"] = review_payload
        return review_payload

    def _render_md(self, p: Dict[str, Any], candidates: List[Dict[str, Any]]) -> str:
        meta = {c["slug"]: c for c in candidates}
        lines = [
            "# Strategy Review",
            "",
            "## Borda Count Vote Tally (composite ranking)",
            "",
            "| Rank | Method | Category | Vote pts | Composite |",
            "|-----:|--------|----------|---------:|----------:|",
        ]
        for i, slug in enumerate(p["rank"], 1):
            c = meta[slug]
            lines.append(
                f"| {i} | {c['name']} | {c['category']} | "
                f"{p['vote_points'].get(slug, 0)} | {p['composite'].get(slug, 0):.3f} |"
            )
        lines += [
            "",
            "## Sample peer reviews (target → reviewers)",
            "",
        ]
        for tgt, revs in list(p["reviews"].items())[:6]:
            lines.append(f"### {tgt}")
            for r in revs:
                lines.append(f"- **{r['reviewer']}** ({'same' if r['same_category'] else 'cross'}): "
                             f"verdict={r['verdict']}, score={r['score']:.2f}")
            lines.append("")
        return "\n".join(lines)
