"""
Meta-Agent.

Section 5.3: closes the feedback loop between predictions and realized outcomes.

In this offline implementation we *log* the proposed self-improvements rather
than overwriting live agent files. A production deployment would gate this
behind sandboxing and human supervisory review.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .base import AgentContext, AgentSpec, BaseAgent


class MetaAgent(BaseAgent):
    SPEC = AgentSpec(
        slug="meta-agent",
        role="Self-improvement loop: feedback, diagnostics, change-log.",
        skills=["meta_learning"],
    )

    def run(self, returns: pd.DataFrame, ac_cma: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare AC-agent expected returns against trailing 3y realized returns.
        Compute simple per-asset prediction error and rank correlation, then
        emit candidate improvements.
        """
        # Trailing 3y window (~756 trading days)
        win = min(len(returns), 756)
        recent = returns.tail(win)
        realized_ann = (1 + recent).prod() ** (252.0 / max(1, win)) - 1.0

        forecasts = {slug: v["expected_return"] for slug, v in ac_cma.items() if slug in realized_ann.index}
        if not forecasts:
            payload = {"feedback": "no overlap", "changes": []}
            self.ctx.save_json("meta/feedback.json", payload)
            return payload

        slugs = list(forecasts.keys())
        f = np.array([forecasts[s] for s in slugs])
        r = np.array([float(realized_ann[s]) for s in slugs])
        err = f - r
        mae = float(np.mean(np.abs(err)))
        # Rank correlation
        rho = _rank_corr(f, r)

        # Heuristic improvement proposals.
        changes: List[Dict[str, Any]] = []
        if rho < 0.0:
            changes.append({
                "target": "skills/cma_judge/cma_methods.py",
                "change": "Reduce confidence weight on inverse_gordon by 0.05 in late-cycle.",
                "reason": f"Cross-sectional rank correlation negative ({rho:.2f}) over trailing {win}d.",
            })
        if mae > 0.06:
            changes.append({
                "target": "skills/cma_judge/SKILL.md",
                "change": "Strengthen valuation tilt rule: PE>28 -> +0.10 valuation weight.",
                "reason": f"Mean absolute prediction error {mae:.2%} exceeds 6% threshold.",
            })
        worst = sorted(zip(slugs, err), key=lambda kv: kv[1], reverse=True)[:3]
        if worst:
            changes.append({
                "target": "agents/asset_class_agent.py",
                "change": f"Add post-judge cap of +200bp above auto-blend for: {[s for s, _ in worst]}.",
                "reason": "Top-3 over-forecast list shows persistent positive bias.",
            })

        payload = {
            "window_days": win,
            "mae": mae,
            "rank_correlation": rho,
            "forecasts": {s: float(forecasts[s]) for s in slugs},
            "realized": {s: float(realized_ann[s]) for s in slugs},
            "errors": {s: float(forecasts[s] - realized_ann[s]) for s in slugs},
            "changes": changes,
        }
        self.ctx.save_json("meta/feedback.json", payload)

        md = ["# Meta-Agent Feedback", "",
              f"- Trailing window: {win} trading days",
              f"- Mean absolute prediction error: **{mae:.2%}**",
              f"- Cross-sectional rank correlation: **{rho:+.2f}**",
              "",
              "## Per-asset error",
              "",
              "| Asset | Forecast | Realized | Error |",
              "|-------|---------:|---------:|------:|"]
        for s in slugs:
            md.append(f"| {s} | {forecasts[s]:.2%} | {realized_ann[s]:.2%} | {forecasts[s] - realized_ann[s]:+.2%} |")
        md.append("")
        md.append("## Proposed Self-Modifications (logged, not executed)\n")
        for ch in changes:
            md.append(f"- **{ch['target']}** — {ch['change']}  \n  _Reason: {ch['reason']}_")
        self.ctx.save_md("meta/feedback.md", "\n".join(md))
        self.log(f"MAE={mae:.2%}, ρ_rank={rho:+.2f}, {len(changes)} change(s) proposed.")
        return payload


def _rank_corr(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    sx = rx.std()
    sy = ry.std()
    if sx <= 0 or sy <= 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])
