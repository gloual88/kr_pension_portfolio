"""
build_slide_charts.py
=====================
유튜브 영상 슬라이드용 PNG 차트 6종 생성.

산출물 (outputs_trimmed10/charts/):
  01_cio_donut.png          - CIO 카테고리 도넛
  02_cio_top_weights.png    - CIO Top 10 비중 가로 막대
  03_risky_dispersion.png   - 21모델 위험자산 비중 가로 막대 (정렬)
  04_avg_vs_cio.png         - 21모델 평균 vs CIO 그룹 막대
  05_category_stack.png     - 21모델 카테고리 stacked bar
  06_macro_scores.png       - 매크로 4축 점수 + late-cycle 라벨
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Tcl/Tk 미설치 환경 대응
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


# ─── 색 ───
COLOR_PRIMARY = "#1F4E79"
COLOR_ACCENT = "#C89B3C"
COLOR_GREY = "#595959"
COLOR_LIGHT_GREY = "#D9D9D9"
COLOR_RED = "#C0392B"
COLOR_GREEN = "#2E7D32"

CAT_COLORS = {
    "Equity": "#1F4E79",
    "FixedIncome": "#7E9BB8",
    "RealAssets": "#C89B3C",
    "Cash": "#5B8A72",
}


def setup_kr_font():
    available = {f.name for f in fm.fontManager.ttflist}
    for name in ["Malgun Gothic", "맑은 고딕", "NanumGothic"]:
        if name in available:
            plt.rcParams["font.family"] = name
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


def chart_donut(weights, cat_of, save_path):
    cats = {"Equity": 0.0, "FixedIncome": 0.0, "RealAssets": 0.0, "Cash": 0.0}
    for s, w in weights.items():
        if cat_of.get(s) in cats:
            cats[cat_of[s]] += w

    fig, ax = plt.subplots(figsize=(7.0, 5.5))
    labels = list(cats.keys())
    vals = [cats[k] * 100 for k in labels]
    colors = [CAT_COLORS[k] for k in labels]

    wedges, texts, autotexts = ax.pie(
        vals, labels=None, autopct="%.1f%%",
        startangle=90, counterclock=False,
        colors=colors, pctdistance=0.78,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2.5),
        textprops=dict(fontsize=14, color="white", fontweight="bold"),
    )

    risky = cats["Equity"] + cats["RealAssets"]
    ax.text(0, 0.05, "위험자산", ha="center", va="center",
            fontsize=13, color=COLOR_GREY)
    ax.text(0, -0.13, f"{risky*100:.1f}%", ha="center", va="center",
            fontsize=28, color=COLOR_PRIMARY, fontweight="bold")
    ax.text(0, -0.30, f"한도 70% — 여유 {(0.70-risky)*100:.0f}%p", ha="center", va="center",
            fontsize=10, color=COLOR_GREEN)

    legend_labels = [f"{k}  {cats[k]*100:.1f}%" for k in labels]
    ax.legend(wedges, legend_labels, loc="center left",
              bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=11)

    ax.set_title("카테고리별 비중 — CIO 최종 (5월호)",
                 fontsize=14, color=COLOR_PRIMARY, fontweight="bold", pad=12)
    plt.tight_layout()
    plt.savefig(save_path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()


def chart_top_weights(weights, etf_label, cat_of, save_path):
    items = sorted(weights.items(), key=lambda x: -x[1])
    labels = [etf_label[s] for s, _ in items]
    vals = [w * 100 for _, w in items]
    colors = [CAT_COLORS[cat_of[s]] for s, _ in items]

    fig, ax = plt.subplots(figsize=(10.0, 5.5))
    y = np.arange(len(labels))
    bars = ax.barh(y, vals, color=colors, edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("비중 (%)", fontsize=11, color=COLOR_GREY)
    ax.set_xlim(0, max(vals) * 1.18)

    for b, v in zip(bars, vals):
        ax.text(v + 0.25, b.get_y() + b.get_height()/2,
                f"{v:.2f}%", va="center", fontsize=11,
                color=COLOR_PRIMARY, fontweight="bold")

    ax.set_title("CIO 최종 — 10 ETF 비중 (내림차순)",
                 fontsize=14, color=COLOR_PRIMARY, fontweight="bold", pad=12)

    handles = [plt.Rectangle((0, 0), 1, 1, color=v) for v in CAT_COLORS.values()]
    ax.legend(handles, list(CAT_COLORS.keys()),
              loc="lower right", frameon=False, fontsize=10)
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()


def chart_risky_dispersion(cat_sums, save_path):
    df = cat_sums.sort_values("Risky(Eq+Real)", ascending=True).copy()
    fig, ax = plt.subplots(figsize=(10.0, 7.5))
    y = np.arange(len(df))
    risky = df["Risky(Eq+Real)"].values
    avg = risky.mean()

    bar_colors = []
    for v in risky:
        if v <= avg - 5:
            bar_colors.append(COLOR_GREEN)
        elif v >= avg + 5:
            bar_colors.append(COLOR_RED)
        else:
            bar_colors.append(COLOR_GREY)

    bars = ax.barh(y, risky, color=bar_colors, edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(df["method"].values, fontsize=10)
    ax.set_xlabel("위험자산(Equity + RealAssets) 비중 (%)",
                  fontsize=11, color=COLOR_GREY)
    ax.set_xlim(0, 75)

    ax.axvline(70, color=COLOR_RED, linestyle="--", linewidth=1.5, alpha=0.7)
    ax.text(70.5, 0.5, "DC/IRP 한도 70%", color=COLOR_RED,
            fontsize=10, fontweight="bold")
    ax.axvline(avg, color=COLOR_PRIMARY, linestyle=":", linewidth=1.5)
    ax.text(avg + 0.5, len(df) - 1.5, f"21모델 평균 {avg:.1f}%",
            color=COLOR_PRIMARY, fontsize=10, fontweight="bold")

    for b, v in zip(bars, risky):
        ax.text(v + 0.5, b.get_y() + b.get_height()/2,
                f"{v:.1f}", va="center", fontsize=9, color=COLOR_GREY)

    ax.set_title("21개 모델의 위험자산 비중 분포",
                 fontsize=14, color=COLOR_PRIMARY, fontweight="bold", pad=12)
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()


def chart_avg_vs_cio(pivot_pct, cio_w, slugs, etf_label, save_path):
    avg = pivot_pct.mean(axis=1)
    cio_arr = np.array([cio_w[s] * 100 for s in slugs])

    df = pd.DataFrame({
        "etf": [etf_label[s] for s in slugs],
        "avg": avg.values,
        "cio": cio_arr,
    })
    df = df.sort_values("avg", ascending=True)

    fig, ax = plt.subplots(figsize=(10.0, 6.5))
    y = np.arange(len(df))
    h = 0.35
    bars1 = ax.barh(y - h/2, df["avg"], h, label="21모델 평균",
                    color=COLOR_LIGHT_GREY, edgecolor="white")
    bars2 = ax.barh(y + h/2, df["cio"], h, label="CIO 최종",
                    color=COLOR_PRIMARY, edgecolor="white")

    ax.set_yticks(y)
    ax.set_yticklabels(df["etf"], fontsize=10)
    ax.set_xlabel("비중 (%)", fontsize=11, color=COLOR_GREY)
    ax.legend(loc="lower right", frameon=False, fontsize=10)

    for b, v in zip(bars1, df["avg"]):
        ax.text(v + 0.2, b.get_y() + b.get_height()/2,
                f"{v:.1f}", va="center", fontsize=9, color=COLOR_GREY)
    for b, v in zip(bars2, df["cio"]):
        ax.text(v + 0.2, b.get_y() + b.get_height()/2,
                f"{v:.1f}", va="center", fontsize=9, color=COLOR_PRIMARY,
                fontweight="bold")

    ax.set_title("21모델 평균 vs CIO 최종 — ETF별 비중 (모든 ETF Δ ≤ 1pp)",
                 fontsize=13, color=COLOR_PRIMARY, fontweight="bold", pad=12)
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()


def chart_category_stack(cat_sums, save_path):
    df = cat_sums.sort_values("Risky(Eq+Real)", ascending=False).copy()
    fig, ax = plt.subplots(figsize=(11.0, 6.0))
    x = np.arange(len(df))
    bottom = np.zeros(len(df))
    for cat, color in [("Equity", CAT_COLORS["Equity"]),
                        ("FixedIncome", CAT_COLORS["FixedIncome"]),
                        ("RealAssets", CAT_COLORS["RealAssets"]),
                        ("Cash", CAT_COLORS["Cash"])]:
        vals = df[cat].values
        ax.bar(x, vals, bottom=bottom, label=cat, color=color, edgecolor="white")
        bottom += vals

    ax.axhline(70, color=COLOR_RED, linestyle="--", linewidth=1.5, alpha=0.7)
    ax.text(len(df) - 1, 71.5, "DC/IRP 위험자산 한도 70%",
            color=COLOR_RED, fontsize=10, fontweight="bold", ha="right")

    ax.set_xticks(x)
    ax.set_xticklabels(df["method"].values, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("비중 (%)", fontsize=11, color=COLOR_GREY)
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right", frameon=False, fontsize=10, ncol=4,
              bbox_to_anchor=(1.0, 1.10))
    ax.set_title("21개 PC 모델의 카테고리 합계 (위험자산 내림차순)",
                 fontsize=14, color=COLOR_PRIMARY, fontweight="bold", pad=22)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()


def chart_macro_scores(macro, save_path):
    scores = macro["scores"]
    keys = ["성장 (growth)", "물가 (inflation)", "통화 (monetary)", "금융 (financial)"]
    vals = [scores["growth"], scores["inflation"],
            scores["monetary"], scores["financial"]]
    colors = [COLOR_GREEN if v > 0 else COLOR_RED for v in vals]

    fig, ax = plt.subplots(figsize=(10.5, 5.0))
    y = np.arange(len(keys))
    bars = ax.barh(y, vals, color=colors, edgecolor="white", height=0.55)
    ax.set_yticks(y)
    ax.set_yticklabels(keys, fontsize=12)
    ax.invert_yaxis()
    ax.axvline(0, color=COLOR_GREY, linewidth=1.0)
    ax.set_xlim(-1.05, 1.05)
    ax.set_xticks([-1.0, -0.5, 0, 0.5, 1.0])
    ax.set_xlabel("점수 (-1: 부정 / +1: 긍정)", fontsize=11, color=COLOR_GREY)

    for b, v in zip(bars, vals):
        ha = "left" if v >= 0 else "right"
        offset = 0.02 if v >= 0 else -0.02
        ax.text(v + offset, b.get_y() + b.get_height()/2,
                f"{v:+.2f}", va="center", ha=ha, fontsize=11,
                color=COLOR_GREY, fontweight="bold")

    title = (f"매크로 레짐: {macro['regime']}  |  "
             f"신뢰도 {macro['confidence']:.2f}  |  "
             f"12m 침체확률 {macro['recession_probability_12m']*100:.0f}%")
    ax.set_title(title, fontsize=13, color=COLOR_PRIMARY,
                 fontweight="bold", pad=12)
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()


def main(out_dir: str) -> None:
    setup_kr_font()
    base = Path(__file__).resolve().parent.parent
    out_path = base / out_dir
    charts_dir = out_path / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    cio = json.loads((out_path / "cio" / "final_portfolio.json").read_text(encoding="utf-8"))
    macro = json.loads((out_path / "macro" / "macro-view.json").read_text(encoding="utf-8"))
    ips = yaml.safe_load((base / "configs" / "ips_trimmed10.yaml").read_text(encoding="utf-8"))

    asset_classes = ips["investment_universe"]["asset_classes"]
    slugs = [ac["slug"] for ac in asset_classes]
    etf_label = {ac["slug"]: f'{ac["etf"]} {ac["etf_name"]}' for ac in asset_classes}
    cat_of = {ac["slug"]: ac["category"] for ac in asset_classes}

    cat_sums = pd.read_csv(out_path / "pc_category_sums_pct.csv")
    pivot_pct = pd.read_csv(out_path / "pc_weights_matrix_pivot_pct.csv", index_col=0)

    chart_donut(cio["weights"], cat_of, charts_dir / "01_cio_donut.png")
    chart_top_weights(cio["weights"], etf_label, cat_of,
                      charts_dir / "02_cio_top_weights.png")
    chart_risky_dispersion(cat_sums, charts_dir / "03_risky_dispersion.png")
    chart_avg_vs_cio(pivot_pct, cio["weights"], slugs, etf_label,
                     charts_dir / "04_avg_vs_cio.png")
    chart_category_stack(cat_sums, charts_dir / "05_category_stack.png")
    chart_macro_scores(macro, charts_dir / "06_macro_scores.png")

    print(f"[done] 6 charts saved to {charts_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="outputs_trimmed10")
    args = parser.parse_args()
    main(out_dir=args.out)
