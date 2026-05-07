"""
Claude LLM wrapper (Korean pension version) — Phase 1: cio_select_ensemble only.

US 버전(self_driving_portfolio/llm/claude_llm.py)을 그대로 가져오되,
prompt에 한국 DC/IRP 연금 컨텍스트 + KR 매크로 키를 반영했습니다.

Subclasses StubLLM: every other method (cma_judge, pc_review) keeps the
deterministic stub behavior, while `cio_select_ensemble` calls Claude.

Look-ahead bias notes:
  - Prompt does NOT include the as_of date or any explicit timestamps.
  - Only the regime label, recession probability, and ensemble diagnostics
    are passed. Claude has no information about the historical period it
    is being asked about.
  - Temperature is 0 for reproducibility.

Cost: ~$0.5 per 18-year backtest with claude-sonnet-4-6 (74 quarters × 1 call).
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict

from .stub_llm import StubLLM, get_llm

LOG = logging.getLogger(__name__)


def _load_env() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    for p in [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]:
        if not p.exists():
            continue
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        if os.environ.get("ANTHROPIC_API_KEY"):
            return


class ClaudeLLM(StubLLM):
    """Real Claude calls only for cio_select_ensemble; everything else stubbed."""

    def __init__(self, model: str = "claude-sonnet-4-6"):
        super().__init__()
        _load_env()
        try:
            from anthropic import Anthropic
        except ImportError:
            raise RuntimeError("anthropic SDK not installed; pip install anthropic")
        self.client = Anthropic()
        self.model = model
        self.call_count = 0

    def cio_select_ensemble(
        self,
        regime: str,
        ensemble_diagnostics: Dict[str, Dict[str, float]],
        macro_readings: Dict[str, float] | None = None,
        recession_probability: float | None = None,
    ) -> Dict[str, Any]:
        valid_choices = list(ensemble_diagnostics.keys())

        diag_lines = []
        for name, d in ensemble_diagnostics.items():
            diag_lines.append(
                f"  - {name}: composite={d.get('composite', 0):.3f}, "
                f"sharpe(BT)={d.get('backtest_sharpe', 0):.2f}, "
                f"vol={d.get('expected_vol', 0)*100:.2f}%, "
                f"MDD(BT)={d.get('backtest_maxdd', 0)*100:.1f}%, "
                f"TE={d.get('tracking_error', 0)*100:.2f}%, "
                f"effN={d.get('effective_n', 0):.1f}, "
                f"IPS_compl={d.get('ips_compliance', 0):.2f}"
            )
        diag_text = "\n".join(diag_lines)

        # Brief description of each ensemble approach (no normative "prefer X in regime Y" guidance).
        ENS_DESCRIPTIONS = {
            "simple_average":     "Equal weight across all PCs. Maximally robust to PC quality dispersion; no tilt.",
            "inverse_te":         "Weight PCs by inverse tracking error to the KOSPI200/KTB10Y 60/40 BM. Tight active risk, BM-anchored.",
            "backtest_sharpe":    "Weight PCs by their backtested Sharpe ratio. Chases past winners.",
            "meta_optimization":  "Solve a meta-optimization to combine PCs into a single MV-efficient blend.",
            "regime_conditional": "Weight PCs by their regime-fit score for the current regime label.",
            "composite_score":    "Weight PCs by their full composite score (Sharpe + IPS + diversification + regime + ...).",
            "trimmed_mean":       "Drop top and bottom PCs by composite score; average the middle. Robust to outliers.",
        }
        desc_text = "\n".join([f"  - {k}: {v}" for k, v in ENS_DESCRIPTIONS.items() if k in valid_choices])

        # KR-specific macro keys (kr_pension_portfolio/scripts/macro_loader_kr.py).
        macro_text = ""
        if macro_readings:
            keys = [
                "kr_gdp_yoy", "kr_cpi_yoy", "kr_core_cpi_yoy",
                "kr_unemployment", "kr_industrial_production_yoy", "kr_exports_yoy",
                "kr_base_rate", "kr_ktb_10y", "kr_ktb_3y", "kr_curve_3y_10y",
                "kr_corp_aa_spread_bp", "kr_usd_krw",
                "us_fed_funds", "us_vix", "kr_brent_oil",
            ]
            available = [(k, macro_readings[k]) for k in keys if k in macro_readings]
            if available:
                macro_text = "Macro readings (Korea + global):\n" + "\n".join(
                    f"  - {k}: {v}" for k, v in available
                ) + "\n\n"

        prec_text = f"12m recession probability estimate: {recession_probability:.0%}\n\n" \
            if recession_probability is not None else ""

        prompt = (
            "You are the CIO of a Korean DC/IRP (defined-contribution / individual "
            "retirement pension) asset manager running an agentic Strategic Asset "
            "Allocation pipeline. The portfolio is constrained to KR-listed ETFs, "
            "with a hard 70% cap on risk assets (Equity + Real Asset) per Korean "
            "pension regulation. The benchmark is KOSPI200 60% / KTB 10Y 40%. "
            "Seven ensemble candidates combine multiple portfolio construction "
            "proposals (PCs) into a single allocation.\n\n"
            f"Macro regime label: **{regime}**\n"
            f"{prec_text}"
            f"{macro_text}"
            "Ensemble candidates — diagnostics:\n"
            f"{diag_text}\n\n"
            "What each ensemble does:\n"
            f"{desc_text}\n\n"
            "Choose ONE ensemble. Use BOTH the Korean macro context (regime label, "
            "recession probability, and the underlying KR + global readings — note "
            "kr_base_rate is the BOK policy rate; kr_curve_3y_10y is the KTB term "
            "spread; kr_corp_aa_spread_bp is the KR corporate AA- credit spread in "
            "bp; kr_usd_krw is the USD/KRW spot) AND the per-ensemble diagnostics "
            "(composite score, backtest Sharpe, drawdown, tracking error, effective "
            "N, IPS compliance vs the 70% risk cap). Make a contextual judgment. "
            "There is no fixed regime→ensemble mapping; weigh the trade-offs given "
            "today's data.\n\n"
            f"Pick exactly ONE name from: {valid_choices}\n\n"
            "Reply ONLY with valid JSON: "
            '{"choice": "<name>", "rationale": "<2-3 sentences>"}'
        )

        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            self.call_count += 1
            text = resp.content[0].text.strip()
            # Strip markdown fences if present.
            if text.startswith("```"):
                lines = text.split("\n")
                start = 1
                end = len(lines) - 1 if lines[-1].startswith("```") else len(lines)
                text = "\n".join(lines[start:end])

            # Find first {...} block (Claude sometimes wraps with prose).
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                text = match.group(0)
            data = json.loads(text)
            choice = data.get("choice")
            if choice not in valid_choices:
                LOG.warning("Claude returned invalid choice '%s'; falling back to stub", choice)
                return super().cio_select_ensemble(regime, ensemble_diagnostics)
            return {
                "choice": choice,
                "rationale": f"[Claude-KR] {data.get('rationale', '')}",
            }
        except Exception as e:
            LOG.warning("Claude call failed (%s); falling back to stub", e)
            return super().cio_select_ensemble(regime, ensemble_diagnostics)


class ClaudeLLMPhase2(ClaudeLLM):
    """Phase 2: CIO selector + CMA judge both call Claude.

    Inherits Phase 1 behavior (cio_select_ensemble) and adds cma_judge
    override. Other methods (peer_review etc.) keep the deterministic stub.

    Cost (KR full backtest, 34 quarters):
      - Phase 1 only:  34 calls (CIO) ≈ $0.5
      - Phase 2:       34 + 18×34 = 646 calls (CIO + 18 asset classes/qtr) ≈ $10~15
    """

    # Per-slug Korean asset-class hint for the prompt (helps LLM contextualize).
    _SLUG_HINTS = {
        "kr-large-cap":        "KOSPI200 (KR equity, domestic)",
        "kr-kosdaq":           "KOSDAQ150 (KR small/mid-cap, growth tilt)",
        "kr-dividend":         "KR dividend-growth (defensive equity)",
        "us-large-cap":        "S&P500 via TIGER 360750 (USD-exposed)",
        "us-tech":             "Nasdaq100 via TIGER 133690 (USD-exposed, growth)",
        "us-dividend":         "US dividend (Dow-style, USD-exposed)",
        "intl-developed":      "MSCI EAFE-style ex-US developed",
        "emerging-markets":    "MSCI EM (USD-exposed, includes KR/CN/IN exposure)",
        "kr-treasuries-10y":   "KTB 10Y (KR sovereign, KRW)",
        "kr-short-bonds":      "KTB ~3M-1Y short duration (KRW cash equiv.)",
        "kr-credit":           "KR aggregate credit (KR corporate AA-)",
        "us-treasuries-10y":   "UST 10Y unhedged (USD-exposed)",
        "us-treasuries-30y":   "UST 30Y currency-hedged (KRW-hedged)",
        "us-ig-credit":        "US IG credit (KRW-hedged)",
        "gold":                "Gold futures (KRW-hedged)",
        "commodities":         "Brent enhanced (KRW-hedged)",
        "kofr-cash":           "KOFR overnight (KR risk-free)",
        "money-market":        "KR money-market active",
    }

    def cma_judge(
        self,
        candidates: Dict[str, float],
        confidences: Dict[str, float],
        regime: str,
        valuation_pe: float | None,
        is_equity: bool,
        slug: str,
        curve_signal: Dict[str, Any] | None = None,
        asset_profile: str | None = None,
    ) -> Dict[str, Any]:
        names = list(candidates.keys())
        if not names:
            return super().cma_judge(candidates, confidences, regime,
                                     valuation_pe, is_equity, slug,
                                     curve_signal=curve_signal, asset_profile=asset_profile)

        vals = [candidates[k] for k in names]
        lo, hi = float(min(vals)), float(max(vals))
        spread_pp = (hi - lo) * 100.0
        dispersion = ("tight" if spread_pp < 3
                      else ("moderate" if spread_pp < 6 else "wide"))

        cand_lines = "\n".join(
            f"  - {k}: estimate={candidates[k]*100:.2f}%, confidence={confidences.get(k, 0.5):.2f}"
            for k in names
        )
        slug_hint = self._SLUG_HINTS.get(slug, slug)
        pe_text = f"Valuation PE (CAPE proxy): {valuation_pe:.1f}\n" if valuation_pe is not None else ""
        curve_text = ""
        if curve_signal:
            curve_text = (
                f"Yield curve state: {curve_signal.get('regime')} / {curve_signal.get('shape')}.\n"
                f"Curve note: {curve_signal.get('notes', '')}\n"
            )

        prompt = (
            "You are setting Capital Market Assumptions (CMA) for a single asset "
            "class in a Korean DC/IRP pension portfolio.\n\n"
            f"Asset class: **{slug}** — {slug_hint}\n"
            f"Type: {'Equity' if is_equity else 'Non-Equity (FixedIncome / RealAsset / Cash)'}\n"
            f"Asset profile: {asset_profile or 'generic'}\n"
            f"Macro regime: **{regime}**\n"
            f"{curve_text}"
            f"{pe_text}"
            f"Spread across methods: {spread_pp:.1f}pp ({dispersion} dispersion)\n\n"
            "Method candidates (annualized expected return, with method confidence):\n"
            f"{cand_lines}\n\n"
            "Choose weights over the methods (must be non-negative; will be "
            "normalized to sum to 1). Use the macro regime, the dispersion "
            "across methods, and the per-method confidence to decide. "
            "Heuristics to consider (not strict rules):\n"
            "  - Late-cycle equity: tilt to valuation-based methods (implied_erp, inverse_gordon).\n"
            "  - Recession: lean on regime_adjusted + bl_equilibrium.\n"
            "  - Wide dispersion: spread weight more evenly (robustness).\n"
            "  - High PE (>30): heavier valuation tilt.\n"
            "  - Low PE (<12): historical_erp + bl_equilibrium tilt.\n"
            "  - Non-equity: use the curve state directly. Bear-flattening should penalize long duration; "
            "bull-steepening can favor duration; cash can dominate when front-end yields rise faster.\n\n"
            f"Method names to weight: {names}\n\n"
            "Reply ONLY with valid JSON: "
            '{"weights": {"<method>": <weight>, ...}, "rationale": "<1-2 sentences>"}'
        )

        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            self.call_count += 1
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                start = 1
                end = len(lines) - 1 if lines[-1].startswith("```") else len(lines)
                text = "\n".join(lines[start:end])
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                text = match.group(0)
            data = json.loads(text)

            raw_w = data.get("weights", {})
            if not isinstance(raw_w, dict):
                raise ValueError("weights not a dict")

            # Filter to known method names; non-negative; normalize.
            weights = {k: max(0.0, float(raw_w.get(k, 0.0))) for k in names}
            s = sum(weights.values())
            if s <= 0:
                raise ValueError("all weights zero")
            weights = {k: v / s for k, v in weights.items()}

            final = float(sum(weights[k] * candidates[k] for k in names))
            final = max(lo, min(hi, final))

            return {
                "final": final,
                "weights": weights,
                "dispersion": dispersion,
                "rationale": f"[Claude-KR-CMA] {data.get('rationale', '')}",
            }
        except Exception as e:
            LOG.warning("Claude cma_judge call failed for %s (%s); falling back to stub",
                        slug, e)
            return super().cma_judge(candidates, confidences, regime,
                                     valuation_pe, is_equity, slug,
                                     curve_signal=curve_signal, asset_profile=asset_profile)


_CLAUDE_INSTANCE: ClaudeLLM | None = None


def install_claude(model: str = "claude-sonnet-4-6") -> ClaudeLLM:
    """Phase 1: install Claude as CIO ensemble selector only.

    After calling this, every `get_llm()` call inside the KR pension pipeline
    returns the Phase 1 wrapper (CMA judge keeps stub behavior).
    Idempotent — repeated calls reuse the same instance.
    """
    global _CLAUDE_INSTANCE
    if _CLAUDE_INSTANCE is None:
        _CLAUDE_INSTANCE = ClaudeLLM(model=model)
        from . import stub_llm
        stub_llm._DEFAULT = _CLAUDE_INSTANCE
    return _CLAUDE_INSTANCE


def install_claude_phase2(model: str = "claude-sonnet-4-6") -> ClaudeLLMPhase2:
    """Phase 2: install Claude as CIO selector + CMA judge.

    Use only when ready to incur ~$10-15 cost per full KR backtest (34 quarters).
    Replaces any prior Phase 1 instance.
    """
    global _CLAUDE_INSTANCE
    _CLAUDE_INSTANCE = ClaudeLLMPhase2(model=model)
    from . import stub_llm
    stub_llm._DEFAULT = _CLAUDE_INSTANCE
    return _CLAUDE_INSTANCE


if __name__ == "__main__":
    # Smoke test
    llm = ClaudeLLM()
    diags = {
        "simple_average":     {"composite": 0.62, "backtest_sharpe": 0.85, "expected_vol": 0.07, "tracking_error": 0.05, "effective_n": 8.0, "ips_compliance": 0.95, "backtest_maxdd": -0.18},
        "inverse_te":         {"composite": 0.65, "backtest_sharpe": 0.80, "expected_vol": 0.07, "tracking_error": 0.04, "effective_n": 7.5, "ips_compliance": 0.98, "backtest_maxdd": -0.16},
        "backtest_sharpe":    {"composite": 0.62, "backtest_sharpe": 0.86, "expected_vol": 0.07, "tracking_error": 0.05, "effective_n": 6.0, "ips_compliance": 0.92, "backtest_maxdd": -0.20},
        "meta_optimization":  {"composite": 0.20, "backtest_sharpe": 0.75, "expected_vol": 0.06, "tracking_error": 0.04, "effective_n": 5.0, "ips_compliance": 0.85, "backtest_maxdd": -0.22},
        "regime_conditional": {"composite": 0.62, "backtest_sharpe": 0.83, "expected_vol": 0.07, "tracking_error": 0.05, "effective_n": 7.0, "ips_compliance": 0.93, "backtest_maxdd": -0.17},
        "composite_score":    {"composite": 0.61, "backtest_sharpe": 0.82, "expected_vol": 0.07, "tracking_error": 0.05, "effective_n": 7.2, "ips_compliance": 0.94, "backtest_maxdd": -0.18},
        "trimmed_mean":       {"composite": 0.60, "backtest_sharpe": 0.80, "expected_vol": 0.07, "tracking_error": 0.05, "effective_n": 6.5, "ips_compliance": 0.93, "backtest_maxdd": -0.18},
    }
    # KR-specific macro snapshot (latest 2026 Q1).
    kr_macro = {
        "kr_gdp_yoy": 3.6,
        "kr_cpi_yoy": 2.16,
        "kr_unemployment": 2.8,
        "kr_base_rate": 2.5,
        "kr_ktb_10y": 3.05,
        "kr_curve_3y_10y": 0.45,
        "kr_corp_aa_spread_bp": 60,
        "kr_usd_krw": 1473.0,
        "kr_exports_yoy": 28.7,
        "us_fed_funds": 4.25,
        "us_vix": 18.5,
        "kr_brent_oil": 78.0,
    }
    for regime in ["expansion", "late-cycle", "recession", "recovery"]:
        out = llm.cio_select_ensemble(regime, diags, macro_readings=kr_macro,
                                       recession_probability=0.20 if regime != "recession" else 0.65)
        print(f"{regime}: choice={out['choice']}")
        print(f"  rationale: {out['rationale']}")
        print()
    print(f"Total calls: {llm.call_count}")
