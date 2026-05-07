"""
Asset Class (AC) Agents.

One agent per asset class (18 instances, see configs/ips.yaml). Each AC agent:
  1. Loads macro view.
  2. Computes historical statistics.
  3. Computes valuation/technical/sentiment signals.
  4. Builds 6 candidate CMA methods (+ auto-blend = 7 total) for equity, or
     4 + auto-blend = 5 total for fixed income / real assets.
  5. Runs the CMA judge (LLM-as-judge stub) to pick / blend.
  6. Writes cma.json, signals.json, historical_stats.json, analysis.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .base import AgentContext, AgentSpec, BaseAgent
from ..llm.stub_llm import get_llm
from ..skills.cma_judge.cma_methods import (
    collect_candidates_equity,
    collect_candidates_fi,
    to_jsonable,
)
from ..skills.historical_analysis.stats import summary_stats
from ..skills.signal_generation.signals import (
    aggregate,
    macro_signal,
    mean_reversion_zscore,
    momentum_signal,
    sentiment_signal,
    trend_signal,
    valuation_signal,
)


# ---------------------------------------------------------------------------
# Asset-class-specific priors used to feed the CMA methods.
# These are intentionally calibrated to roughly reproduce the figures in
# Exhibit 8 of the paper for the equity asset classes.
# ---------------------------------------------------------------------------
EQUITY_PRIORS: Dict[str, Dict[str, float]] = {
    "us-large-cap":     {"hist_erp": 0.088, "div_yield": 0.014, "earn_growth": 0.045, "val_change": -0.016, "cape": 25.0, "consensus": 0.073, "mkt_w": 0.30, "lam": 2.5},
    "us-growth":        {"hist_erp": 0.096, "div_yield": 0.009, "earn_growth": 0.058, "val_change": -0.032, "cape": 31.0, "consensus": 0.080, "mkt_w": 0.18, "lam": 2.5},
    "us-value":         {"hist_erp": 0.080, "div_yield": 0.022, "earn_growth": 0.040, "val_change": -0.014, "cape": 20.0, "consensus": 0.070, "mkt_w": 0.12, "lam": 2.5},
    "us-small-cap":     {"hist_erp": 0.084, "div_yield": 0.018, "earn_growth": 0.043, "val_change": -0.005, "cape": 18.0, "consensus": 0.070, "mkt_w": 0.05, "lam": 2.5},
    "intl-developed":   {"hist_erp": 0.040, "div_yield": 0.030, "earn_growth": 0.030, "val_change": +0.006, "cape": 17.5, "consensus": 0.066, "mkt_w": 0.15, "lam": 2.5},
    "emerging-markets": {"hist_erp": 0.072, "div_yield": 0.030, "earn_growth": 0.060, "val_change": -0.021, "cape": 13.0, "consensus": 0.069, "mkt_w": 0.08, "lam": 2.5},
    "reits":            {"hist_erp": 0.084, "div_yield": 0.040, "earn_growth": 0.030, "val_change": +0.001, "cape": 29.0, "consensus": 0.072, "mkt_w": 0.04, "lam": 2.5},
}


FI_PRIORS: Dict[str, Dict[str, float]] = {
    "short-treasuries":        {"ytw": 0.040, "rolldown": -0.002, "term_premium": 0.000, "hist_ret": 0.029},
    "intermediate-treasuries": {"ytw": 0.041, "rolldown": +0.005, "term_premium": +0.005, "hist_ret": 0.046},
    "long-treasuries":         {"ytw": 0.043, "rolldown": +0.008, "term_premium": +0.010, "hist_ret": 0.061},
    "ig-corporates":           {"ytw": 0.052, "rolldown": +0.005, "term_premium": +0.005, "hist_ret": 0.055},
    "hy-corporates":           {"ytw": 0.072, "rolldown": +0.000, "term_premium": +0.005, "hist_ret": 0.072},
    "intl-sovereigns":         {"ytw": 0.038, "rolldown": +0.003, "term_premium": +0.005, "hist_ret": 0.041},
    "intl-corporates":         {"ytw": 0.045, "rolldown": +0.003, "term_premium": +0.005, "hist_ret": 0.044},
    "usd-em-debt":             {"ytw": 0.067, "rolldown": +0.000, "term_premium": +0.005, "hist_ret": 0.067},
}


REAL_ASSETS_PRIORS: Dict[str, Dict[str, float]] = {
    "gold":        {"ytw": 0.045, "rolldown": 0.0,  "term_premium": 0.005, "hist_ret": 0.067},
    "commodities": {"ytw": 0.030, "rolldown": 0.0,  "term_premium": 0.010, "hist_ret": 0.038},
    "cash":        {"ytw": 0.038, "rolldown": 0.0,  "term_premium": 0.0,   "hist_ret": 0.024},
}


def _slug_seed(slug: str) -> int:
    return abs(hash(slug)) % 99991


class AssetClassAgent(BaseAgent):
    """One instance per asset class entry in IPS."""

    def __init__(self, ctx: AgentContext, asset_class: dict, prices: pd.DataFrame, returns: pd.DataFrame):
        self.ac = asset_class
        self.prices = prices
        self.returns = returns
        self.SPEC = AgentSpec(
            slug=f"ac::{asset_class['slug']}",
            role=f"Produces CMAs and investment-case memo for {asset_class['name']}.",
            skills=["historical_analysis", "signal_generation", "cma_judge",
                    "equity_analysis" if asset_class["category"] == "Equity" else "fixed_income_analysis"],
        )
        super().__init__(ctx)

    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        slug = self.ac["slug"]
        cat = self.ac["category"]
        macro_view = self.ctx.artifacts["macro_view"]

        # 1. Historical analysis
        if slug not in self.returns.columns:
            self.log(f"WARN: missing returns column {slug}, skipping")
            return {}
        hs = summary_stats(self.returns[[slug]])[slug]

        # 2. Signals
        sigs = self._signals(slug, macro_view)

        # 3. Candidate CMA methods
        if cat == "Equity":
            methods = self._equity_methods(slug, macro_view)
            cape = EQUITY_PRIORS.get(slug, {}).get("cape", 18.0)
            is_equity = True
        else:
            methods = self._non_equity_methods(slug, macro_view)
            cape = None
            is_equity = False

        # 4. CMA Judge (LLM-as-judge stub)
        candidates = {k: v.estimate for k, v in methods.items()}
        confidences = {k: v.confidence for k, v in methods.items()}
        judge_out = get_llm().cma_judge(
            candidates=candidates,
            confidences=confidences,
            regime=macro_view["regime"],
            valuation_pe=cape,
            is_equity=is_equity,
            slug=slug,
            curve_signal=None,
            asset_profile=self._asset_profile(),
        )

        # 5. Persist
        self.ctx.save_json(f"asset_classes/{slug}/historical_stats.json", hs)
        self.ctx.save_json(f"asset_classes/{slug}/signals.json", sigs)
        self.ctx.save_json(f"asset_classes/{slug}/cma_methods.json", to_jsonable(methods))

        cma_payload = {
            "slug": slug,
            "name": self.ac["name"],
            "category": cat,
            "expected_return": float(judge_out["final"]),
            "expected_volatility": float(hs["vol_ann"]),
            "confidence": 0.55,
            "regime": macro_view["regime"],
            "curve_regime": macro_view.get("curve_signal", {}).get("regime"),
            "method_weights": judge_out["weights"],
            "rationale": judge_out["rationale"],
            "dispersion": judge_out["dispersion"],
            "candidates": {k: float(v.estimate) for k, v in methods.items()},
        }
        self.ctx.save_json(f"asset_classes/{slug}/cma.json", cma_payload)
        self.ctx.save_md(
            f"asset_classes/{slug}/analysis.md",
            self._render_md(cma_payload, methods, hs, sigs, macro_view),
        )

        # Make available to downstream agents.
        self.ctx.artifacts.setdefault("ac_cma", {})[slug] = cma_payload
        self.log(f"E[r]={cma_payload['expected_return']:.2%} σ={cma_payload['expected_volatility']:.2%} ({cma_payload['dispersion']})")
        return cma_payload

    # ------------------------------------------------------------------
    def _signals(self, slug: str, macro_view: dict) -> Dict[str, float]:
        prices_s = self.prices[slug] if slug in self.prices.columns else None
        sens = self.ac.get("macro_sensitivity", {})
        sigs: Dict[str, float] = {}
        sigs["macro"] = macro_signal(macro_view["scores"], sens)
        if prices_s is not None:
            sigs["momentum"] = momentum_signal(prices_s)
            sigs["trend"] = trend_signal(prices_s)
            sigs["mean_reversion"] = mean_reversion_zscore(prices_s)
        sigs["sentiment"] = sentiment_signal(_slug_seed(slug))
        if self.ac["category"] == "Equity":
            cape = EQUITY_PRIORS.get(slug, {}).get("cape")
            if cape:
                sigs["valuation"] = valuation_signal(cape)
        return aggregate(sigs)

    def _asset_profile(self) -> str:
        slug = self.ac["slug"]
        cat = self.ac["category"]
        if cat == "Cash" or slug in {"kofr-cash", "money-market", "kr-short-bonds"}:
            return "cash"
        if slug in {"kr-treasuries-10y", "us-treasuries-10y", "us-treasuries-30y"}:
            return "long_duration"
        if "credit" in slug or "ig" in slug:
            return "credit"
        if cat == "RealAssets":
            return "real_asset"
        return "credit"

    def _equity_methods(self, slug: str, macro_view: dict):
        p = EQUITY_PRIORS.get(slug, {
            "hist_erp": 0.06, "div_yield": 0.02, "earn_growth": 0.04, "val_change": 0.0,
            "cape": 20.0, "consensus": 0.07, "mkt_w": 0.05, "lam": 2.5,
        })
        rf = self.ctx.config.get("rf", 0.040)
        cov_diag = float(self.returns[slug].std() ** 2 * 252) if slug in self.returns else 0.025
        return collect_candidates_equity(
            historical_premium=p["hist_erp"],
            rf=rf,
            regime=macro_view["regime"],
            market_cap_weight=p["mkt_w"],
            cov_diag=cov_diag,
            lam=p["lam"],
            div_yield=p["div_yield"],
            earn_growth=p["earn_growth"],
            valuation_change=p["val_change"],
            cape=p["cape"],
            consensus=p["consensus"],
        )

    def _non_equity_methods(self, slug: str, macro_view: dict):
        p = FI_PRIORS.get(slug) or REAL_ASSETS_PRIORS.get(slug)
        if not p:
            p = {"ytw": 0.04, "rolldown": 0.0, "term_premium": 0.005, "hist_ret": 0.04}
        return collect_candidates_fi(
            yield_to_worst=p["ytw"],
            rolldown=p["rolldown"],
            term_premium=p["term_premium"],
            historical_return=p["hist_ret"],
            regime=macro_view["regime"],
            curve_signal=None,
            asset_profile=self._asset_profile(),
        )

    # ------------------------------------------------------------------
    def _render_md(self, cma, methods, hs, sigs, macro_view) -> str:
        lines = [
            f"# Asset Class — {self.ac['name']}",
            "",
            f"**Slug:** `{self.ac['slug']}`  ",
            f"**Category:** {self.ac['category']}  ",
            f"**ETF:** {self.ac.get('etf', 'n/a')}  ",
            f"**Regime context:** {macro_view['regime']} (P(rec) {macro_view['recession_probability_12m']:.0%})  ",
            f"**Yield-curve context:** {macro_view.get('curve_signal', {}).get('regime', 'n/a')}",
            "",
            "## CMA Decision",
            "",
            f"- Expected return (3y, nominal): **{cma['expected_return']:.2%}**",
            f"- Expected volatility (annualized): **{cma['expected_volatility']:.2%}**",
            f"- Dispersion across methods: {cma['dispersion']}",
            f"- Rationale: {cma['rationale']}",
            "",
            "### Method weights (judge)",
            "",
            "| Method | Weight | Estimate |",
            "|--------|--------|----------|",
        ]
        for m, w in cma["method_weights"].items():
            est = cma["candidates"].get(m, float("nan"))
            lines.append(f"| {m} | {w:.0%} | {est:.2%} |")
        lines += [
            "",
            "## Historical Statistics (annualized)",
            "",
            f"- Mean: {hs['mean_ann']:.2%}",
            f"- Volatility: {hs['vol_ann']:.2%}",
            f"- Sharpe: {hs['sharpe']:.2f}",
            f"- Max drawdown: {hs['max_drawdown']:.1%}",
            "",
            "## Signals",
            "",
        ]
        for k, v in sigs.items():
            lines.append(f"- {k}: {v:+.2f}")
        return "\n".join(lines)
