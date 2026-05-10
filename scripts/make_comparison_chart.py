"""3-line NAV comparison chart for the production brief.

Outputs: docs/lock70_nav_comparison.png  (baseline / Phase 2 / KR 60/40 BM)
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import json

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

base = Path(__file__).resolve().parents[1]
bl_dir = base / "outputs" / "backtest_kr_lock70"
p2_dir = base / "outputs" / "backtest_kr_lock70_llm_phase2"


def _nav(p):
    return pd.read_csv(p, parse_dates=["date"]).set_index("date").iloc[:, 0]


bl = _nav(bl_dir / "nav_agentic.csv")
bm = _nav(bl_dir / "nav_benchmark.csv")
p2 = _nav(p2_dir / "nav_agentic.csv")

with open(bl_dir / "metrics.json", encoding="utf-8") as f:
    bl_m = json.load(f)
with open(p2_dir / "metrics.json", encoding="utf-8") as f:
    p2_m = json.load(f)

# Common index
idx = bl.index.intersection(p2.index).intersection(bm.index)
bl, p2, bm = bl.loc[idx], p2.loc[idx], bm.loc[idx]

fig, ax = plt.subplots(figsize=(11, 5.8))
ax.plot(bm.index, bm.values, lw=1.4, color="#A8A8A8", linestyle="--",
        label=f"KR 60/40 BM (Sharpe {bl_m['benchmark_kr_60_40']['sharpe']:.3f})")
ax.plot(bl.index, bl.values, lw=1.7, color="#1F4E79",
        label=f"AI 자율 baseline ★ (Sharpe {bl_m['agentic']['sharpe']:.3f})")
ax.plot(p2.index, p2.values, lw=1.7, color="#C89B3C",
        label=f"AI 자율 Phase 2 LLM (Sharpe {p2_m['agentic']['sharpe']:.3f})")

ax.set_title("Walk-forward 백테스트 — 위험자산 70% lock (2018-01 ~ 2026-05, 34 분기 QS)",
             fontsize=13, color="#1F4E79", fontweight="bold")
ax.set_ylabel("NAV (시작점 1.0)", fontsize=11)
ax.set_xlabel("")
ax.grid(alpha=0.3)
ax.legend(loc="upper left", fontsize=10, framealpha=0.95)
ax.set_facecolor("#FAFAFA")

# Annotation for final values
last = idx[-1]
ax.annotate(f"+{(bl.iloc[-1]-1)*100:.1f}%", xy=(last, bl.iloc[-1]),
            xytext=(8, 0), textcoords="offset points",
            fontsize=9, color="#1F4E79", fontweight="bold", va="center")
ax.annotate(f"+{(p2.iloc[-1]-1)*100:.1f}%", xy=(last, p2.iloc[-1]),
            xytext=(8, 12), textcoords="offset points",
            fontsize=9, color="#C89B3C", fontweight="bold", va="center")
ax.annotate(f"+{(bm.iloc[-1]-1)*100:.1f}%", xy=(last, bm.iloc[-1]),
            xytext=(8, 0), textcoords="offset points",
            fontsize=9, color="#888888", va="center")

fig.tight_layout()
out = base / "docs" / "lock70_nav_comparison.png"
fig.savefig(str(out), dpi=160)
plt.close(fig)
print(f"Written: {out}")
