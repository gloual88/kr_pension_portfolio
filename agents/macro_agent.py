"""KR Macro Agent — adapted for Korean pension investor."""
from __future__ import annotations

from typing import Any, Dict

from .base import AgentContext, AgentSpec, BaseAgent
from ..skills.macro_regime.regime_kr import (
    KR_DEFAULT_READINGS,
    classify_curve_signal_kr,
    classify_regime_kr,
    recession_probability_kr,
)


class MacroAgent(BaseAgent):
    SPEC = AgentSpec(
        slug="macro-agent",
        role="KR macro regime classifier (BOK + KOSPI + global proxies).",
        skills=["macro_regime"],
        inputs=["KR macro readings via ECOS+FRED auto-fetch; static fallback"],
        outputs=["macro/macro-view.json", "macro/analysis.md"],
    )

    def run(self) -> Dict[str, Any]:
        readings = self.ctx.config.get("macro_readings")
        provenance: Dict[str, str] = {}
        if readings is None:
            if self.ctx.config.get("macro_live_fetch", True):
                try:
                    from ..scripts.macro_loader_kr import fetch_latest_macro_readings_kr
                    readings = fetch_latest_macro_readings_kr(KR_DEFAULT_READINGS)
                    provenance = readings.pop("_fetch_provenance", {})
                    n_live = len(provenance)
                    self.log(f"Live fetched {n_live}/{len(KR_DEFAULT_READINGS)} KR macro indicators")
                except Exception as e:
                    self.log(f"Live fetch failed ({e}); using static KR fallback readings")
                    readings = dict(KR_DEFAULT_READINGS)
            else:
                readings = dict(KR_DEFAULT_READINGS)

        result = classify_regime_kr(readings)
        curve_signal = classify_curve_signal_kr(readings)
        p_rec = recession_probability_kr(readings)

        payload = {
            "regime": result.regime,
            "confidence": round(result.confidence, 3),
            "scores": {k: round(v, 3) for k, v in result.scores.items()},
            "recession_probability_12m": round(p_rec, 3),
            "readings": readings,
            "curve_signal": curve_signal,
            "provenance": provenance,
            "notes": result.notes,
        }
        self.ctx.save_json("macro/macro-view.json", payload)
        self.ctx.save_md("macro/analysis.md", self._render_md(payload))
        self.ctx.artifacts["macro_view"] = payload
        self.log(
            f"Regime={payload['regime']} (conf {payload['confidence']:.2f}, "
            f"P(rec)={payload['recession_probability_12m']:.0%}, "
            f"curve={curve_signal['regime']})"
        )
        return payload

    def _render_md(self, p: Dict[str, Any]) -> str:
        lines = [
            "# KR 거시경제 레짐 분석 (Self-Driving Pension Portfolio)",
            "",
            f"**Regime:** {p['regime']}",
            f"**Confidence:** {p['confidence']:.2f}",
            f"**P(recession 12m):** {p['recession_probability_12m']:.0%}",
            "",
            "## 4-Dimension Scores",
            "",
            "| Dimension | Score |",
            "|-----------|-------|",
        ]
        for k, v in p["scores"].items():
            lines.append(f"| {k} | {v:+.2f} |")
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        lines.append(p["notes"])
        lines.append("")
        if p.get("curve_signal"):
            cs = p["curve_signal"]
            lines.append("## Yield Curve Signal")
            lines.append("")
            lines.append(f"- State: {cs['regime']}")
            lines.append(f"- Shape: {cs['shape']}")
            lines.append(f"- Note: {cs['notes']}")
            lines.append("")
        lines.append("## Key Readings")
        lines.append("")
        prov = p.get("provenance", {})
        if prov:
            lines.append("| Indicator | Value | Source |")
            lines.append("|-----------|-------|--------|")
            for k, v in p["readings"].items():
                src = prov.get(k, "static fallback")
                lines.append(f"| {k} | {v} | {src} |")
        else:
            lines.append("| Indicator | Value |")
            lines.append("|-----------|-------|")
            for k, v in p["readings"].items():
                lines.append(f"| {k} | {v} |")
        return "\n".join(lines)
