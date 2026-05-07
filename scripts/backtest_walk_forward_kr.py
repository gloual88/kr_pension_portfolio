"""
Walk-forward backtester for the Korean DC/IRP pension SAA pipeline.

Each rebalance date t:
  1. Build KR macro readings as known on t (publication-lag aware) from the
     pre-fetched ECOS+FRED panel.
  2. Slice the KR price panel to dates < t.
  3. Run a *minimal* pipeline (Macro → AssetClass CMA → Covariance →
     PC + Researcher → CIO ensemble) and capture the CIO weight w_t.
  4. Hold w_t until the next rebalance, with daily NAV updates.

Cost model: turnover * cost_bp on each rebalance.
Benchmark: 60% kr-large-cap (KOSPI200) + 40% kr-treasuries-10y (KTB 10Y).

Variants:
  - baseline: stub LLM (deterministic regime→ensemble mapping)
  - llm:      Claude as cio_select_ensemble (Phase 1)
"""
from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from kr_pension_portfolio.agents.asset_class_agent import AssetClassAgent
from kr_pension_portfolio.agents.base import AgentContext
from kr_pension_portfolio.agents.cio_agent import CIOAgent
from kr_pension_portfolio.agents.covariance_agent import CovarianceAgent
from kr_pension_portfolio.agents.cro_agent import CROAgent
from kr_pension_portfolio.agents.macro_agent import MacroAgent
from kr_pension_portfolio.agents.pc_agents import PCAgent, PCResearcherAgent
from kr_pension_portfolio.agents.strategy_review_agent import StrategyReviewAgent
from kr_pension_portfolio.scripts.data_loader_kr import load_universe_kr
from kr_pension_portfolio.scripts.macro_loader_kr import (
    historical_macro_panel_kr,
    readings_as_of_kr,
    KR_FALLBACK_READINGS,
)
from kr_pension_portfolio.skills.pc_methods.pc_engine import make_constraints

warnings.filterwarnings("ignore")


def _benchmark_kr_60_40(asset_classes: List[dict]) -> np.ndarray:
    """KR DC/IRP standard benchmark: KOSPI200 60% + KTB 10Y 40%."""
    n = len(asset_classes)
    w = np.zeros(n)
    for i, ac in enumerate(asset_classes):
        if ac["slug"] == "kr-large-cap":
            w[i] = 0.60
        elif ac["slug"] == "kr-treasuries-10y":
            w[i] = 0.40
    return w


def _run_quarter(
    as_of: pd.Timestamp,
    macro_panel: Dict[str, pd.Series],
    full_prices: pd.DataFrame,
    full_returns: pd.DataFrame,
    asset_classes: List[dict],
    pc_cfg: dict,
    ips: dict,
    out_root: Path,
    benchmark_w: np.ndarray,
) -> Dict:
    """Run the minimal KR pipeline as of `as_of` and return CIO weight + diagnostics."""
    slugs = [ac["slug"] for ac in asset_classes]
    prices_t = full_prices[full_prices.index < as_of]
    returns_t = full_returns[full_returns.index < as_of]
    if len(prices_t) < 252:
        return {"as_of": as_of, "skipped": True, "reason": "insufficient history"}

    quarter_dir = out_root / "quarters" / as_of.strftime("%Y-%m-%d")
    quarter_dir.mkdir(parents=True, exist_ok=True)

    readings = readings_as_of_kr(macro_panel, as_of, KR_FALLBACK_READINGS)
    ctx_config = {
        "ips": ips, "rf": 0.030,                # KR risk-free ≈ KOFR/Cash 3%
        "macro_readings": readings,
        "macro_live_fetch": False,
    }
    ctx = AgentContext(output_root=quarter_dir, config=ctx_config)

    # 1. Macro
    macro_payload = MacroAgent(ctx).run()

    # 2. AC agents — only on slugs with > 280 daily obs (momentum 252 + skip 21 + buffer)
    valid_slugs = [s for s in slugs if s in returns_t.columns
                   and returns_t[s].dropna().shape[0] > 280]
    valid_acs = [ac for ac in asset_classes if ac["slug"] in valid_slugs]
    for ac in valid_acs:
        AssetClassAgent(ctx, ac, prices_t, returns_t).run()

    # 3. Covariance
    returns_v = returns_t.reindex(columns=valid_slugs).dropna(how="all")
    CovarianceAgent(ctx, returns_v).run()

    # 4. PC researcher
    PCResearcherAgent(ctx).run()

    Sigma = ctx.artifacts["covariance"]["Sigma"]
    mu = np.array([ctx.artifacts["ac_cma"][s]["expected_return"] for s in valid_slugs])

    cb = ips.get("constraints", {}).get("category_bounds", {})
    cat_min = {k: v.get("min", 0.0) for k, v in cb.items()}
    cat_max = {k: v.get("max", 1.0) for k, v in cb.items()}
    pos = ips.get("constraints", {}).get("position_limits", {})
    cons = make_constraints(valid_acs,
                            pos_min=pos.get("min", 0.0),
                            pos_max=pos.get("max", 0.30),
                            cat_min=cat_min, cat_max=cat_max)

    bm_v = np.array([benchmark_w[slugs.index(s)] for s in valid_slugs])
    if bm_v.sum() > 0:
        bm_v = bm_v / bm_v.sum()

    # 5. PC agents
    parallel = [e for e in pc_cfg["pc_agents"] if not e.get("runs_after_others")]
    adversarial_entry = next((e for e in pc_cfg["pc_agents"] if e.get("runs_after_others")), None)

    pc_results = []
    for entry in parallel:
        agent = PCAgent(ctx, entry, mu, Sigma, returns_v, cons, valid_acs, bm_v)
        pc_results.append(agent.run())
    if adversarial_entry is not None:
        agent = PCAgent(ctx, adversarial_entry, mu, Sigma, returns_v, cons, valid_acs, bm_v)
        pc_results.append(agent.run(others=[r.weights for r in pc_results]))

    # 6. CRO
    CROAgent(ctx).run(pc_results)

    # 7. Strategy review
    review = StrategyReviewAgent(ctx).run(pc_results)

    # 8. CIO
    cio_payload = CIOAgent(ctx).run(
        pc_results=pc_results, Sigma=Sigma, mu=mu, returns=returns_v,
        asset_classes=valid_acs, review_payload=review, ips=ips, benchmark_w=bm_v,
    )

    final_w_dict = cio_payload["weights"]
    weight_full = {s: float(final_w_dict.get(s, 0.0)) for s in slugs}

    return {
        "as_of": as_of,
        "skipped": False,
        "regime": macro_payload["regime"],
        "regime_conf": macro_payload["confidence"],
        "p_rec": macro_payload["recession_probability_12m"],
        "chosen_ensemble": cio_payload["chosen_ensemble"],
        "weights": weight_full,
        "metrics": cio_payload.get("metrics", {}),
    }


def main(
    start: str = "2018-01-01",
    end: Optional[str] = None,
    rebalance_freq: str = "QS",
    cost_bp: float = 5.0,
    out_root: str = "outputs/backtest_kr",
    smoke: bool = False,
    variant: str = "baseline",
    macro_start: str = "2010-01-01",
):
    base = Path(__file__).resolve().parents[1]
    cfg_path = base / "configs" / "ips.yaml"
    pc_cfg_path = base / "configs" / "pc_agents.yaml"

    if variant == "llm":
        out_root = out_root.rstrip("/") + "_llm"
    elif variant == "llm_phase2":
        out_root = out_root.rstrip("/") + "_llm_phase2"
    out_path = base / out_root
    out_path.mkdir(parents=True, exist_ok=True)

    with open(cfg_path, "r", encoding="utf-8") as f:
        ips = yaml.safe_load(f)
    with open(pc_cfg_path, "r", encoding="utf-8") as f:
        pc_cfg = yaml.safe_load(f)

    if variant == "llm":
        from kr_pension_portfolio.llm.claude_llm import install_claude
        install_claude(model="claude-sonnet-4-6")
        print("[backtest-kr] Claude LLM installed for cio_select_ensemble (Phase 1)")
    elif variant == "llm_phase2":
        from kr_pension_portfolio.llm.claude_llm import install_claude_phase2
        install_claude_phase2(model="claude-sonnet-4-6")
        print("[backtest-kr] Claude LLM installed for CIO + CMA judge (Phase 2)")
        print("[backtest-kr] Estimated cost: ~$10-15 for 34 quarters")
    print(f"[backtest-kr] variant={variant}, IPS={cfg_path.name}, out={out_path}")

    asset_classes = ips["investment_universe"]["asset_classes"]
    slugs = [ac["slug"] for ac in asset_classes]

    print(f"[backtest-kr] loading prices for {len(asset_classes)} KR-listed ETFs …")
    data = load_universe_kr(asset_classes, prefer="yfinance")
    print(f"[backtest-kr] price panel shape: {data.prices.shape}, source={data.source}")

    print(f"[backtest-kr] fetching historical macro panel from ECOS+FRED (start={macro_start}) …")
    t0 = time.time()
    macro_panel = historical_macro_panel_kr(start=macro_start)
    print(f"[backtest-kr] macro panel ready ({time.time()-t0:.0f}s, "
          f"{sum(len(s) > 0 for s in macro_panel.values())}/{len(macro_panel)} series)")

    end = end or pd.Timestamp.today().normalize().strftime("%Y-%m-%d")
    rebal_dates = pd.date_range(start, end, freq=rebalance_freq)
    if smoke:
        rebal_dates = rebal_dates[:3]
    print(f"[backtest-kr] {len(rebal_dates)} rebalance dates from {rebal_dates[0].date()} to {rebal_dates[-1].date()}")

    benchmark_w = _benchmark_kr_60_40(asset_classes)

    quarter_runs = []
    for i, t in enumerate(rebal_dates):
        t0 = time.time()
        result = _run_quarter(t, macro_panel, data.prices, data.returns,
                              asset_classes, pc_cfg, ips, out_path, benchmark_w)
        elapsed = time.time() - t0
        if result.get("skipped"):
            print(f"[{i+1:2d}/{len(rebal_dates)}] {t.date()} SKIPPED: {result.get('reason')}")
            continue
        print(f"[{i+1:2d}/{len(rebal_dates)}] {t.date()} regime={result['regime']:<11} "
              f"conf={result['regime_conf']:.2f} ens={result['chosen_ensemble']:<22} ({elapsed:.1f}s)")
        quarter_runs.append(result)

    if not quarter_runs:
        print("[backtest-kr] No successful quarter runs — aborting.")
        return

    # ----- NAV simulation -----
    weights_df = pd.DataFrame(
        {q["as_of"]: q["weights"] for q in quarter_runs}
    ).T.reindex(columns=slugs).fillna(0.0)
    weights_df.index = pd.to_datetime(weights_df.index)

    daily = data.returns.fillna(0.0).reindex(columns=slugs).fillna(0.0)
    daily = daily[(daily.index >= weights_df.index[0]) & (daily.index <= pd.Timestamp(end))]

    port_ret = pd.Series(0.0, index=daily.index)
    bm_ret = pd.Series(0.0, index=daily.index)

    cur_w = None
    next_idx = 0
    rebal_index = list(weights_df.index)
    cost_total = 0.0
    turnover_total = 0.0

    bm_w = pd.Series(benchmark_w, index=slugs)

    for date in daily.index:
        while next_idx < len(rebal_index) and date >= rebal_index[next_idx]:
            new_w = weights_df.iloc[next_idx]
            if cur_w is not None:
                turnover = float(np.abs(new_w.values - cur_w.values).sum())
                cost = turnover * cost_bp / 10000.0
                port_ret.loc[date] -= cost
                cost_total += cost
                turnover_total += turnover
            cur_w = new_w
            next_idx += 1
        if cur_w is not None:
            r = float((cur_w.values * daily.loc[date].values).sum())
            port_ret.loc[date] += r
        bm_ret.loc[date] = float((bm_w.values * daily.loc[date].values).sum())

    nav = (1.0 + port_ret).cumprod()
    bm_nav = (1.0 + bm_ret).cumprod()

    def perf(ret: pd.Series) -> Dict:
        ann_ret = float((1.0 + ret.mean()) ** 252 - 1.0)
        ann_vol = float(ret.std(ddof=0) * np.sqrt(252))
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
        cum = (1.0 + ret).cumprod()
        peaks = cum.cummax()
        mdd = float((cum / peaks - 1.0).min())
        return {
            "ann_return": ann_ret, "ann_vol": ann_vol,
            "sharpe": sharpe, "max_drawdown": mdd,
            "total_return": float(cum.iloc[-1] - 1.0),
        }

    metrics = {
        "agentic": perf(port_ret),
        "benchmark_kr_60_40": perf(bm_ret),
        "n_rebalances": len(quarter_runs),
        "total_turnover": turnover_total,
        "total_cost": cost_total,
        "avg_turnover_per_rebal": turnover_total / max(len(quarter_runs), 1),
        "variant": variant,
    }

    weights_df.to_csv(out_path / "weights_quarterly.csv", index_label="date")
    nav.rename("agentic").to_csv(out_path / "nav_agentic.csv", index_label="date")
    bm_nav.rename("benchmark").to_csv(out_path / "nav_benchmark.csv", index_label="date")
    pd.DataFrame({
        "as_of": [q["as_of"] for q in quarter_runs],
        "regime": [q["regime"] for q in quarter_runs],
        "regime_conf": [q["regime_conf"] for q in quarter_runs],
        "p_rec": [q["p_rec"] for q in quarter_runs],
        "ensemble": [q["chosen_ensemble"] for q in quarter_runs],
    }).to_csv(out_path / "regime_history.csv", index=False)

    with open(out_path / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=float)

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(nav.index, nav.values, label=f"Agentic SAA ({variant})", lw=1.6, color="#1f4e79")
    ax.plot(bm_nav.index, bm_nav.values, label="60/40 BM (KOSPI200/KTB10Y)",
            lw=1.4, color="#a8a8a8", linestyle="--")
    ax.set_title(f"KR Pension Walk-Forward — Agentic ({variant}) vs KR 60/40\n"
                 f"{rebal_dates[0].date()} – {rebal_dates[-1].date()}, "
                 f"Sharpe {metrics['agentic']['sharpe']:.2f} vs "
                 f"{metrics['benchmark_kr_60_40']['sharpe']:.2f}")
    ax.set_ylabel("NAV (start = 1.0)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path / "equity_curve.png", dpi=140)
    plt.close(fig)

    print()
    print("=" * 72)
    print(f"KR Pension Walk-Forward Backtest SUMMARY ({variant})")
    print("=" * 72)
    print(f"Period: {nav.index[0].date()} → {nav.index[-1].date()}, "
          f"rebalances={len(quarter_runs)} ({rebalance_freq})")
    print()
    print(f"{'':<22} {'Agentic':>12} {'KR 60/40':>12}")
    for k in ["ann_return", "ann_vol", "sharpe", "max_drawdown", "total_return"]:
        a = metrics["agentic"][k]
        b = metrics["benchmark_kr_60_40"][k]
        if k in ("ann_return", "ann_vol", "max_drawdown", "total_return"):
            print(f"{k:<22} {a*100:>11.2f}% {b*100:>11.2f}%")
        else:
            print(f"{k:<22} {a:>12.3f} {b:>12.3f}")
    print(f"\nAvg turnover per rebal: {metrics['avg_turnover_per_rebal']:.2%}")
    print(f"Total cost (bp): {metrics['total_cost']*10000:.0f} bp")
    print(f"\nOutputs at: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2018-01-01",
                        help="First rebalance date (KR ETF history begins ~2017)")
    parser.add_argument("--end", default=None)
    parser.add_argument("--freq", default="QS", help="Pandas freq alias (QS, MS, AS)")
    parser.add_argument("--cost-bp", type=float, default=5.0)
    parser.add_argument("--smoke", action="store_true",
                        help="Run only first 3 rebalances (smoke test)")
    parser.add_argument("--out", default="outputs/backtest_kr")
    parser.add_argument("--variant", default="baseline",
                        choices=["baseline", "llm", "llm_phase2"],
                        help="baseline: stub LLM; "
                             "llm: Claude as CIO selector only (Phase 1, ~$0.5); "
                             "llm_phase2: Claude as CIO + CMA judge (~$10-15)")
    parser.add_argument("--macro-start", default="2010-01-01",
                        help="ECOS+FRED panel start date (>= 5y before --start)")
    args = parser.parse_args()
    main(start=args.start, end=args.end, rebalance_freq=args.freq,
         cost_bp=args.cost_bp, smoke=args.smoke, out_root=args.out,
         variant=args.variant, macro_start=args.macro_start)
