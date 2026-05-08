"""
2026-04-01 분기 리밸런싱 포트폴리오 시각화 (한달 전 제안)

소스: outputs/backtest_kr/quarters/2026-04-01/cio/final_portfolio.json
"""
from __future__ import annotations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
import numpy as np
import yaml

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(r"d:\파이선\kr_pension_portfolio")
SNAP = ROOT / "outputs" / "backtest_kr" / "quarters" / "2026-04-01"
OUT_PNG = ROOT / "outputs" / "april_2026_portfolio.png"

# IPS 메타 (slug → ETF code/name/category)
ips = yaml.safe_load((ROOT / "configs" / "ips.yaml").read_text(encoding="utf-8"))
META = {a["slug"]: a for a in ips["investment_universe"]["asset_classes"]}

# Final portfolio
fp = json.loads((SNAP / "cio" / "final_portfolio.json").read_text(encoding="utf-8"))
weights = fp["weights"]
m = fp["metrics"]

# Long-form table
rows = []
for slug, w in weights.items():
    a = META[slug]
    rows.append({
        "slug": slug,
        "category": a["category"],
        "etf": a["etf"],
        "etf_name": a["etf_name"],
        "weight": w * 100,
    })
rows.sort(key=lambda r: r["weight"], reverse=True)

CAT_COLORS = {
    "Equity":      "#2E86AB",
    "FixedIncome": "#5C9E5E",
    "RealAssets":  "#D4A017",
    "Cash":        "#7F8C8D",
}
CAT_KO = {
    "Equity": "주식", "FixedIncome": "채권",
    "RealAssets": "실물자산", "Cash": "현금성",
}

# Category aggregation
cat_sum = {}
for r in rows:
    cat_sum[r["category"]] = cat_sum.get(r["category"], 0) + r["weight"]

# ─────────────────────────────────────────────────────────────
# Figure
# ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 9), dpi=130)
fig.patch.set_facecolor("white")
gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.4],
                      width_ratios=[1.2, 1, 1],
                      hspace=0.32, wspace=0.32)

# === [TOP-LEFT] 카테고리 도넛 ===
axA = fig.add_subplot(gs[0, 0])
labels = list(cat_sum.keys())
sizes  = [cat_sum[k] for k in labels]
colors = [CAT_COLORS[k] for k in labels]
wedges, _ = axA.pie(sizes, colors=colors, startangle=90,
                    wedgeprops=dict(width=0.32, edgecolor="white", linewidth=2))
axA.text(0, 0.06, "위험자산", ha="center", fontsize=10, color="#555")
risky_pct = cat_sum.get("Equity", 0) + cat_sum.get("RealAssets", 0)
axA.text(0, -0.10, f"{risky_pct:.0f}%",
         ha="center", fontsize=22, fontweight="bold", color="#222")
axA.text(0, -0.27, "DC/IRP 한도 70%", ha="center",
         fontsize=8.5, color="#888")
axA.set_title("카테고리 비중", fontsize=11, fontweight="bold", pad=8, loc="left")

# 외부 라벨
for w, lbl, sz in zip(wedges, labels, sizes):
    ang = (w.theta2 + w.theta1) / 2
    x = 1.15 * np.cos(np.deg2rad(ang))
    y = 1.15 * np.sin(np.deg2rad(ang))
    ha = "left" if x >= 0 else "right"
    axA.text(x, y, f"{CAT_KO[lbl]}\n{sz:.1f}%",
             ha=ha, va="center", fontsize=9, fontweight="bold",
             color=CAT_COLORS[lbl])

# === [TOP-MID/RIGHT] 핵심 지표 + 매크로 ===
axM = fig.add_subplot(gs[0, 1:])
axM.axis("off")

# Macro panel
macro_text = (
    "■ 매크로 (2026-04 기준)\n"
    "• 레짐 :  late-cycle (conf 0.57, P(rec) 20%)\n"
    "• 성장 :  GDP +3.6%   수출 +28.7%   실업 2.7%\n"
    "• 인플레: CPI +2.2%   유가 $119.6   USD/KRW 1,530\n"
    "• 통화 :  BOK 2.50%   KTB10Y 3.69%   AA-spread 64bp\n"
    "• 글로벌: Fed 3.64%   VIX 24.5"
)
axM.text(0.0, 1.0, macro_text, transform=axM.transAxes,
         fontsize=9.5, va="top",
         color="#222",
         bbox=dict(boxstyle="round,pad=0.6", facecolor="#F7F9FB",
                   edgecolor="#D6DCE3"))

# Metrics panel
metrics_text = (
    "■ 포트폴리오 지표 (CIO 선택: inverse_te 앙상블)\n"
    f"• E[r]  3y : {m['expected_return']*100:>5.2f}%       (60/40 BM 대비 ↓)\n"
    f"• σ        : {m['expected_vol']*100:>5.2f}%       IPS 하한 6% 미만\n"
    f"• BT Sharpe: {m['backtest_sharpe']:>5.2f}        (BM 1.37)\n"
    f"• BT MDD   : {m['backtest_maxdd']*100:>5.1f}%       (BM −13.5%)\n"
    f"• Tracking : {m['tracking_error']*100:>5.2f}%       (budget 6.0%)\n"
    f"• Eff. N   : {m['effective_n']:>5.1f}        (분산도 양호)"
)
axM.text(0.55, 1.0, metrics_text, transform=axM.transAxes,
         fontsize=9.5, va="top",
         color="#222",
         bbox=dict(boxstyle="round,pad=0.6", facecolor="#FFF7EC",
                   edgecolor="#E8C988"))

# === [BOTTOM] ETF별 비중 가로 막대 ===
axB = fig.add_subplot(gs[1, :])

ys = np.arange(len(rows))[::-1]
ws = [r["weight"] for r in rows]
cs = [CAT_COLORS[r["category"]] for r in rows]
labels_left = [f"{r['etf_name']}  ({r['etf']})" for r in rows]

bars = axB.barh(ys, ws, color=cs, edgecolor="white", linewidth=0.6)

axB.set_yticks(ys)
axB.set_yticklabels(labels_left, fontsize=9.2)
axB.invert_yaxis()
axB.set_xlim(0, max(ws) * 1.18)
axB.set_xlabel("비중 (%)", fontsize=10)

for bar, w, r in zip(bars, ws, rows):
    axB.text(w + 0.18, bar.get_y() + bar.get_height() / 2,
             f"{w:.2f}%",
             va="center", fontsize=9, color="#333", fontweight="bold")

axB.spines["top"].set_visible(False)
axB.spines["right"].set_visible(False)
axB.spines["left"].set_color("#bbb")
axB.spines["bottom"].set_color("#bbb")
axB.tick_params(colors="#444")
axB.grid(axis="x", color="#ececec", linewidth=0.6)

# 카테고리 범례
from matplotlib.patches import Patch
handles = [Patch(facecolor=CAT_COLORS[k], label=f"{CAT_KO[k]} {cat_sum[k]:.1f}%")
           for k in ["Equity", "FixedIncome", "RealAssets", "Cash"] if k in cat_sum]
axB.legend(handles=handles, loc="lower right", frameon=False,
           fontsize=9, ncol=4)
axB.set_title("ETF별 권장 비중 — 2026년 4월 분기 리밸런싱",
              loc="left", fontsize=12, fontweight="bold", pad=10)

# Suptitle
fig.suptitle("KR 연금 자율주행 포트폴리오 — 2026-04-01 (한달 전 제안)",
             fontsize=15, fontweight="bold", y=0.98)

fig.text(0.012, 0.005,
         f"Source: kr_pension_portfolio backtest_kr/quarters/2026-04-01  |  "
         f"CIO 앙상블: {fp['chosen_ensemble']}  |  18 KR-listed ETFs",
         fontsize=8.5, color="#666")

plt.subplots_adjust(left=0.03, right=0.98, top=0.93, bottom=0.06)
plt.savefig(OUT_PNG, dpi=160, bbox_inches="tight", facecolor="white")
plt.close()
print(f"Saved: {OUT_PNG}")

# 콘솔 요약
print("\n=== 2026-04-01 포트폴리오 (한달 전 제안) ===\n")
print(f"앙상블: {fp['chosen_ensemble']}")
print(f"E[r] {m['expected_return']*100:.2f}%  σ {m['expected_vol']*100:.2f}%  "
      f"Sharpe {m['backtest_sharpe']:.2f}  MDD {m['backtest_maxdd']*100:.1f}%\n")
print(f"{'순위':>3} {'카테고리':10} {'ETF code':<8} {'ETF 이름':32} {'비중':>7}")
print("-" * 70)
for i, r in enumerate(rows, 1):
    print(f"{i:>3} {CAT_KO[r['category']]:10} {r['etf']:<8} {r['etf_name']:30}  {r['weight']:>6.2f}%")
print("-" * 70)
for k, v in cat_sum.items():
    print(f"  {CAT_KO[k]:<10}: {v:>6.2f}%")
print(f"  {'위험자산':<10}: {risky_pct:>6.2f}%   (DC/IRP 한도 70%)")
