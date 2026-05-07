"""
CRO Agent.

Section 3.5: produces a standardized risk report for each candidate portfolio
(vol, VaR, MaxDD, concentration, factor tilts, IPS compliance). The CRO is a
neutral assessor — it does NOT vote.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from .base import AgentContext, AgentSpec, BaseAgent


class CROAgent(BaseAgent):
    SPEC = AgentSpec(
        slug="cro-agent",
        role="Neutral risk assessor; produces standardized risk reports per candidate.",
        skills=["risk_assessment"],
    )

    def run(self, candidates: List[Any]) -> Dict[str, Any]:
        reports: Dict[str, Dict[str, Any]] = {}
        for r in candidates:
            metrics = r.metrics
            ips_flags = metrics.get("ips_flags", [])
            severity = "OK" if not ips_flags else ("YELLOW" if len(ips_flags) <= 2 else "RED")
            commentary = (
                f"σ={metrics['ex_ante_vol']:.2%}, VaR95={metrics['ex_ante_var95']:.2%}, "
                f"backtestDD={metrics['backtest_maxdd']:.1%}, EffN={metrics['effective_n']:.1f}. "
                f"Compliance flags: {len(ips_flags)} ({severity})."
            )
            reports[r.slug] = {
                "slug": r.slug,
                "name": r.name,
                "category": r.category,
                "metrics": metrics,
                "severity": severity,
                "commentary": commentary,
            }
        self.ctx.save_json("cro/risk_reports.json", reports)
        md = ["# CRO Risk Reports", ""]
        for r in reports.values():
            md.append(f"## {r['name']} ({r['category']})\n")
            md.append(f"- Severity: **{r['severity']}**")
            md.append(f"- {r['commentary']}\n")
        self.ctx.save_md("cro/risk_reports.md", "\n".join(md))
        self.log(f"Issued {len(reports)} risk reports.")
        self.ctx.artifacts["cro_reports"] = reports
        return reports
