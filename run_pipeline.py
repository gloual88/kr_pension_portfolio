"""
Self-Driving Pension Portfolio — KR pipeline runner.

Korean adaptation of the agentic SAA pipeline:
  - 18 KR-listed ETFs (DC/IRP eligible)
  - Macro: ECOS + FRED hybrid (15 KR + global indicators)
  - Benchmark: KOSPI 200 60% + KTB 10Y 40%
  - DC/IRP regulatory cap: risky assets ≤ 70%
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import List

import numpy as np
import yaml

# Import path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from kr_pension_portfolio.agents.asset_class_agent import AssetClassAgent
from kr_pension_portfolio.agents.base import AgentContext
from kr_pension_portfolio.agents.cio_agent import CIOAgent
from kr_pension_portfolio.agents.covariance_agent import CovarianceAgent
from kr_pension_portfolio.agents.cro_agent import CROAgent
from kr_pension_portfolio.agents.macro_agent import MacroAgent
from kr_pension_portfolio.agents.meta_agent import MetaAgent
from kr_pension_portfolio.agents.pc_agents import PCAgent, PCResearcherAgent
from kr_pension_portfolio.agents.strategy_review_agent import StrategyReviewAgent
from kr_pension_portfolio.scripts.data_loader_kr import load_universe_kr
from kr_pension_portfolio.skills.pc_methods.pc_engine import (
    Constraints, adversarial_diversifier, make_constraints,
)


def _benchmark_kr_60_40(asset_classes: List[dict]) -> np.ndarray:
    """KR 60/40: KOSPI 200 60% + KTB 10Y 40%."""
    n = len(asset_classes)
    w = np.zeros(n)
    for i, ac in enumerate(asset_classes):
        if ac["slug"] == "kr-large-cap":
            w[i] = 0.60
        elif ac["slug"] == "kr-treasuries-10y":
            w[i] = 0.40
    if w.sum() <= 0:
        eq_i = next((i for i, ac in enumerate(asset_classes) if ac["category"] == "Equity"), 0)
        ti = next((i for i, ac in enumerate(asset_classes) if ac["category"] == "FixedIncome"), 1)
        w[eq_i] = 0.6
        w[ti] = 0.4
    return w


def main(prefer_data: str = "yfinance", out_root: str = "outputs",
         ips_file: str = "ips.yaml") -> None:
    t0 = time.time()
    base = Path(__file__).resolve().parent
    cfg_path = base / "configs" / ips_file
    pc_cfg_path = base / "configs" / "pc_agents.yaml"
    out_path = base / out_root
    out_path.mkdir(parents=True, exist_ok=True)

    with open(cfg_path, "r", encoding="utf-8") as f:
        ips = yaml.safe_load(f)
    with open(pc_cfg_path, "r", encoding="utf-8") as f:
        pc_cfg = yaml.safe_load(f)

    asset_classes = ips["investment_universe"]["asset_classes"]
    n_ac = len(asset_classes)
    print(f"[pipeline] loading KR universe ({n_ac} ETFs), prefer={prefer_data}")
    data = load_universe_kr(asset_classes, prefer=prefer_data)
    slugs = [ac["slug"] for ac in asset_classes]
    returns = data.returns.reindex(columns=slugs).dropna(how="all")
    prices = data.prices.reindex(columns=slugs)
    print(f"[pipeline] data source={data.source}, returns shape={returns.shape}")

    ctx = AgentContext(output_root=out_path, config={
        "ips": ips,
        "rf": 0.0250,  # KR risk-free roughly = BOK base ~2.5%
    })

    # 1. Macro agent — KR
    print("\n[1/10] Macro agent (KR)")
    MacroAgent(ctx).run()

    # 2. Asset class agents
    print(f"\n[2/10] Asset class agents ({n_ac})")
    for ac in asset_classes:
        AssetClassAgent(ctx, ac, prices, returns).run()

    # 3. Covariance agent
    print("\n[3/10] Covariance agent")
    CovarianceAgent(ctx, returns).run()

    # 4. PC-Researcher
    print("\n[4/10] PC-Researcher")
    PCResearcherAgent(ctx).run()

    # Build mu / Sigma
    Sigma = ctx.artifacts["covariance"]["Sigma"]
    mu = np.array([ctx.artifacts["ac_cma"][s]["expected_return"] for s in slugs])

    # Constraints (DC/IRP: Equity 55% + RealAssets 15% = 70% risky cap)
    cb = ips.get("constraints", {}).get("category_bounds", {})
    cat_min = {k: v.get("min", 0.0) for k, v in cb.items()}
    cat_max = {k: v.get("max", 1.0) for k, v in cb.items()}
    pos = ips.get("constraints", {}).get("position_limits", {})
    cons = make_constraints(asset_classes,
                            pos_min=pos.get("min", 0.0),
                            pos_max=pos.get("max", 0.25),
                            cat_min=cat_min, cat_max=cat_max)

    benchmark_w = _benchmark_kr_60_40(asset_classes)

    # 5. PC agents
    print(f"\n[5/10] PC agents ({len(pc_cfg['pc_agents'])})")
    pc_results = []
    parallel: list = []
    adversarial_entry = None
    for entry in pc_cfg["pc_agents"]:
        if entry.get("runs_after_others"):
            adversarial_entry = entry
        else:
            parallel.append(entry)
    for entry in parallel:
        agent = PCAgent(ctx, entry, mu, Sigma, returns, cons, asset_classes, benchmark_w)
        pc_results.append(agent.run())

    if adversarial_entry is not None:
        agent = PCAgent(ctx, adversarial_entry, mu, Sigma, returns, cons, asset_classes, benchmark_w)
        pc_results.append(agent.run(others=[r.weights for r in pc_results]))

    # 6. CRO agent
    print("\n[6/10] CRO agent")
    CROAgent(ctx).run(pc_results)

    # 7. Strategy review
    print("\n[7/10] Strategy review")
    review = StrategyReviewAgent(ctx).run(pc_results)

    # 8. Top-5 revision
    print("\n[8/10] Top-5 revision")
    top5 = review["rank"][:5]
    mu_revised = mu.copy()
    for slug in top5:
        r = next((x for x in pc_results if x.slug == slug), None)
        if r is None:
            continue
        top_idx = int(np.argmax(r.weights))
        mu_revised[top_idx] += 0.0025
    revised: list = []
    for entry in parallel:
        if entry["slug"] in top5:
            agent = PCAgent(ctx, entry, mu_revised, Sigma, returns, cons, asset_classes, benchmark_w)
            r = agent.run()
            ctx.save_json(f"pc/{entry['slug']}/proposal_revised.json",
                          {"weights": {ac["slug"]: float(r.weights[i]) for i, ac in enumerate(asset_classes)}})
            revised.append(r)
        else:
            r = next((x for x in pc_results if x.slug == entry["slug"]), None)
            if r:
                revised.append(r)
    if adversarial_entry is not None:
        adv = next((x for x in pc_results if x.slug == adversarial_entry["slug"]), None)
        if adv is not None:
            revised.append(adv)
    pc_results = revised

    # 9. CIO agent
    print("\n[9/10] CIO agent")
    CIOAgent(ctx).run(
        pc_results=pc_results, Sigma=Sigma, mu=mu, returns=returns,
        asset_classes=asset_classes, review_payload=review, ips=ips, benchmark_w=benchmark_w,
    )

    # 10. Meta-agent
    print("\n[10/10] Meta-agent")
    MetaAgent(ctx).run(returns, ctx.artifacts["ac_cma"])

    elapsed = time.time() - t0
    print(f"\n[pipeline] done in {elapsed:.1f}s")
    print(f"[pipeline] outputs at {out_path}")
    print(f"[pipeline] board memo: {out_path / 'cio' / 'board_memo.md'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="yfinance", choices=["auto", "yfinance"])
    parser.add_argument("--out", default="outputs")
    parser.add_argument("--ips", default="ips.yaml",
                        help="IPS yaml filename under configs/ (e.g. ips_trimmed10.yaml)")
    args = parser.parse_args()
    main(prefer_data=args.data, out_root=args.out, ips_file=args.ips)
