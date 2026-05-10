"""
월간 연금 포트폴리오 — 10-ETF 축약 유니버스 기반 21개 PC 모델 비교.

데이터 소스: kr_pension_portfolio/outputs_trimmed10/
  - cio/final_portfolio.json          : CIO 최종 추천 (월간 포트폴리오)
  - pc/<slug>/proposal[_revised].json : 21개 모델 각자 비중
  - macro/macro-view.json             : 매크로 regime
  - pc_weights_matrix_pivot_pct.csv   : ETF×Method 매트릭스 (사전 집계)
  - pc_category_sums_pct.csv          : 모델별 카테고리 합계
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import CATEGORY_COLORS, render_sidebar


# ============================================================
# 경로 / 로더
# ============================================================
DASH_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = DASH_DIR.parent
TRIMMED_OUT = PROJECT_DIR / "outputs_trimmed10"
TRIMMED_IPS = PROJECT_DIR / "configs" / "ips_trimmed10.yaml"
PC_AGENTS_CFG = PROJECT_DIR / "configs" / "pc_agents.yaml"


@st.cache_data(show_spinner=False)
def _load_yaml(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@st.cache_data(show_spinner=False)
def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def _load_pc_proposals(out_dir: Path, pc_cfg: dict) -> pd.DataFrame:
    """모든 PC 모델의 비중을 (method, name, category, etf...) 행으로 수집."""
    rows = []
    for entry in pc_cfg["pc_agents"]:
        slug = entry["slug"]
        prop_rev = out_dir / "pc" / slug / "proposal_revised.json"
        prop = out_dir / "pc" / slug / "proposal.json"
        path = prop_rev if prop_rev.exists() else prop
        if not path.exists():
            continue
        d = _load_json(path) or {}
        weights = d.get("weights", {})
        rows.append({"method": slug, "name": entry["name"],
                     "category": entry["category"], **weights})
    return pd.DataFrame(rows)


def _category_totals(weights: Dict[str, float], cat_of: Dict[str, str]) -> Dict[str, float]:
    totals = {"Equity": 0.0, "FixedIncome": 0.0, "RealAssets": 0.0, "Cash": 0.0}
    for slug, w in weights.items():
        c = cat_of.get(slug)
        if c in totals:
            totals[c] += float(w)
    return totals


# ============================================================
# 페이지
# ============================================================
st.set_page_config(page_title="월간 연금 포트폴리오 — KR", layout="wide")
render_sidebar()

st.title("월간 연금 포트폴리오")
st.caption("10-ETF 축약 유니버스 (구독자 가독성 강화) — 21개 PC 모델 비중 비교 + CIO 최종 추천")

# --- 데이터 로드 ---
ips = _load_yaml(TRIMMED_IPS)
pc_cfg = _load_yaml(PC_AGENTS_CFG)
cio = _load_json(TRIMMED_OUT / "cio" / "final_portfolio.json")
macro = _load_json(TRIMMED_OUT / "macro" / "macro-view.json")
board_memo = (TRIMMED_OUT / "cio" / "board_memo.md")
board_memo_text = board_memo.read_text(encoding="utf-8") if board_memo.exists() else None

if ips is None or cio is None or pc_cfg is None:
    st.error(
        "축약(10-ETF) 결과 부재. 다음을 실행하세요:\n\n"
        "```\n"
        "cd d:\\파이선\n"
        "& \"d:\\파이선\\pykrx_venv\\Scripts\\python.exe\" -m kr_pension_portfolio.run_pipeline "
        "--data yfinance --ips ips_trimmed10.yaml --out outputs_trimmed10\n"
        "& \"d:\\파이선\\pykrx_venv\\Scripts\\python.exe\" -m "
        "kr_pension_portfolio.scripts.aggregate_pc_weights "
        "--out outputs_trimmed10 --ips ips_trimmed10.yaml\n"
        "```"
    )
    st.stop()

# 메타
asset_classes = ips["investment_universe"]["asset_classes"]
slugs = [ac["slug"] for ac in asset_classes]
etf_label = {ac["slug"]: f'{ac["etf"]} {ac["etf_name"]}' for ac in asset_classes}
short_label = {ac["slug"]: ac["etf_name"] for ac in asset_classes}
cat_of = {ac["slug"]: ac["category"] for ac in asset_classes}

cio_w = cio["weights"]
cio_m = cio["metrics"]
chosen = cio["chosen_ensemble"]

# --- 헤더: 월 / 산출 시각 / regime ---
final_path = TRIMMED_OUT / "cio" / "final_portfolio.json"
import datetime as _dt
gen_ts = _dt.datetime.fromtimestamp(final_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

regime = macro.get("regime", "n/a") if macro else "n/a"
conf = macro.get("confidence", 0.0) if macro else 0.0
p_rec = macro.get("recession_probability_12m", 0.0) if macro else 0.0

cat_totals = _category_totals(cio_w, cat_of)
risk_w = cat_totals["Equity"] + cat_totals["RealAssets"]

st.info(
    f"**산출 시각**: {gen_ts}  |  "
    f"**선택 ensemble**: `{chosen}`  |  "
    f"**거시 레짐**: {regime} (신뢰도 {conf:.2f}, 12m 침체확률 {p_rec*100:.0f}%)"
)

# KPI
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("위험자산 비중",
              f"{risk_w*100:.1f}%",
              "CIO mandate: lock 70%",
              delta_color="off")
with c2:
    st.metric("기대 수익률 (E[r])",
              f"{cio_m.get('expected_return', 0)*100:.2f}%",
              f"σ {cio_m.get('expected_vol', 0)*100:.2f}%", delta_color="off")
with c3:
    st.metric("BT Sharpe",
              f"{cio_m.get('backtest_sharpe', 0):.2f}",
              f"MDD {cio_m.get('backtest_maxdd', 0)*100:.2f}%", delta_color="off")
with c4:
    st.metric("Tracking Error",
              f"{cio_m.get('tracking_error', 0)*100:.2f}%",
              f"분산도(div) {cio_m.get('diversification', 0):.2f}", delta_color="off")

st.markdown("---")

# ============================================================
# 1. CIO 최종 포트폴리오 (월간 추천)
# ============================================================
st.subheader("1. 이번 달 추천 포트폴리오 — CIO 최종")

c1, c2 = st.columns([3, 2])
with c1:
    fig = go.Figure(data=[go.Pie(
        labels=list(cat_totals.keys()),
        values=list(cat_totals.values()),
        hole=0.45,
        marker=dict(colors=[CATEGORY_COLORS[k] for k in cat_totals.keys()]),
        textinfo="label+percent",
        textposition="outside",
        sort=False,
    )])
    fig.update_layout(height=380, margin=dict(t=20, b=10, l=10, r=10), showlegend=False,
                      title_text="카테고리별 비중")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    rows = [{"ETF": etf_label[s], "카테고리": cat_of[s], "비중": cio_w.get(s, 0.0)}
            for s in slugs]
    df_w = pd.DataFrame(rows).sort_values("비중", ascending=False)
    df_w["비중"] = df_w["비중"].apply(lambda x: f"{x*100:.2f}%")
    st.dataframe(df_w, hide_index=True, use_container_width=True, height=380)

st.caption(f"DC/IRP lock70: Equity {cat_totals['Equity']*100:.1f}% + "
           f"RealAssets {cat_totals['RealAssets']*100:.1f}% = "
           f"**{risk_w*100:.1f}%** (CIO mandate target 70%)")

# ------------------------------------------------------------
# 1b. FI 수익률곡선 재배분 (FI 합계 보존)
# ------------------------------------------------------------
tilt = cio.get("fi_curve_tilt") or {}
if tilt.get("applied"):
    st.markdown("---")
    st.subheader("1b. FI 수익률곡선 재배분 (FI 합계 보존)")
    curve = (macro or {}).get("curve_signal") or {}
    st.caption(
        f"곡선 레짐 `{tilt['regime']}` · 형태 `{curve.get('shape', 'n/a')}` · "
        f"FI 카테고리 합계 {tilt['fi_total']*100:.2f}% 유지 · 비-FI 자산군 비중 변동 없음"
    )

    pre_w = cio.get("weights_pre_tilt", {})
    post_w = cio.get("weights", {})

    def _profile(slug):
        if slug in {"kr-treasuries-10y", "us-treasuries-10y", "us-treasuries-30y"}:
            return "long_duration"
        if slug == "kr-short-bonds":
            return "cash_like"
        return "credit"

    rows = []
    for slug, dpp in sorted(tilt["shifts_pp"].items(), key=lambda kv: kv[1]):
        rows.append({
            "FI ETF": etf_label.get(slug, slug),
            "프로필": _profile(slug),
            "Pre-tilt (%)": pre_w.get(slug, 0.0) * 100,
            "Post-tilt (%)": post_w.get(slug, 0.0) * 100,
            "Δ (pp)": dpp,
        })
    df_tilt = pd.DataFrame(rows)

    c1, c2 = st.columns([3, 2])
    with c1:
        fig_tilt = go.Figure()
        fig_tilt.add_trace(go.Bar(
            y=df_tilt["FI ETF"], x=df_tilt["Pre-tilt (%)"],
            orientation="h", name="Pre-tilt (옵티마이저 산출)",
            marker_color="#9bb5d1",
            hovertemplate="Pre: %{x:.2f}%<extra></extra>",
        ))
        fig_tilt.add_trace(go.Bar(
            y=df_tilt["FI ETF"], x=df_tilt["Post-tilt (%)"],
            orientation="h", name="Post-tilt (곡선 반영)",
            marker_color="#1f4e79",
            hovertemplate="Post: %{x:.2f}%<extra></extra>",
        ))
        fig_tilt.update_layout(
            barmode="group", height=320,
            margin=dict(t=20, b=10, l=10, r=10),
            xaxis=dict(title="비중 (%)"),
            yaxis=dict(autorange="reversed"),
            legend=dict(orientation="h", y=1.05, x=0),
        )
        st.plotly_chart(fig_tilt, use_container_width=True)
    with c2:
        view = df_tilt.copy()
        view["Pre-tilt (%)"] = view["Pre-tilt (%)"].apply(lambda x: f"{x:.2f}")
        view["Post-tilt (%)"] = view["Post-tilt (%)"].apply(lambda x: f"{x:.2f}")
        view["Δ (pp)"] = view["Δ (pp)"].apply(lambda x: f"{x:+.2f}")
        st.dataframe(view, hide_index=True, use_container_width=True, height=320)

    rules = tilt.get("rules") or {}
    rule_str = " · ".join(f"{k}×{v:.2f}" for k, v in rules.items())
    st.caption(
        f"Tilt 룰: {rule_str}. CIO 옵티마이저는 곡선 영향을 받지 않은 μ로 산출되고, "
        "곡선 신호는 FI 카테고리 내부에서만 사후 재분배됩니다. "
        "Equity/RealAssets/Cash 비중은 Pre = Post."
    )

st.markdown("---")

# ============================================================
# 2. 21개 모델 비중 히트맵
# ============================================================
st.subheader("2. 21개 PC 모델별 비중 — Heatmap")

df_pc = _load_pc_proposals(TRIMMED_OUT, pc_cfg)
if df_pc.empty:
    st.warning("PC 모델 산출물(proposal.json) 부재.")
else:
    weight_cols = [s for s in slugs if s in df_pc.columns]
    # 모델 카테고리 순서로 정렬
    cat_order = ["A_Heuristic", "B_ReturnOptimized", "C_RiskStructured",
                 "D_NonTraditional", "E_Researcher"]
    df_pc["category"] = pd.Categorical(df_pc["category"], categories=cat_order, ordered=True)
    df_pc = df_pc.sort_values(["category", "method"])

    methods = df_pc["method"].tolist()
    matrix = df_pc[weight_cols].values * 100  # %
    yticks = [short_label[s] for s in weight_cols]

    heat = go.Figure(data=go.Heatmap(
        z=matrix.T,
        x=methods,
        y=yticks,
        colorscale="Blues",
        colorbar=dict(title="%"),
        hovertemplate="모델: %{x}<br>ETF: %{y}<br>비중: %{z:.2f}%<extra></extra>",
        zmin=0, zmax=25,
        text=[[f"{v:.1f}" if v >= 1.0 else "" for v in row] for row in matrix.T],
        texttemplate="%{text}",
        textfont=dict(size=10),
    ))
    heat.update_layout(
        height=440, margin=dict(t=10, b=10, l=10, r=10),
        xaxis=dict(tickangle=-45, side="bottom"),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(heat, use_container_width=True)

    st.caption("색이 진할수록 비중이 큰 종목. lock70 IPS 제약(Equity 55% lock, RealAssets 15% lock, "
               "FI 25-30%, Cash ≤5%, position ≤25%) 하에서 21개 모델이 카테고리 *내부* 분배만 결정.")

st.markdown("---")

# ============================================================
# 3. 모델별 카테고리 합계 — 막대그래프
# ============================================================
st.subheader("3. 모델별 카테고리 합계 (위험자산 vs 안전자산)")

if not df_pc.empty:
    cat_rows = []
    for _, r in df_pc.iterrows():
        cs = {"method": r["method"]}
        for c in {"Equity", "FixedIncome", "RealAssets", "Cash"}:
            cs[c] = sum(r[s] for s in weight_cols if cat_of[s] == c) * 100
        cs["Risky"] = cs["Equity"] + cs["RealAssets"]
        cat_rows.append(cs)
    cat_df = pd.DataFrame(cat_rows)

    fig_cat = go.Figure()
    for c in ["Equity", "FixedIncome", "RealAssets", "Cash"]:
        fig_cat.add_trace(go.Bar(
            name=c, x=cat_df["method"], y=cat_df[c],
            marker_color=CATEGORY_COLORS[c],
            hovertemplate=f"{c}: %{{y:.1f}}%<extra></extra>",
        ))
    fig_cat.add_hline(y=70, line=dict(color="red", dash="dash"),
                      annotation_text="DC/IRP 위험자산 한도 70%",
                      annotation_position="top right")
    fig_cat.update_layout(
        barmode="stack", height=360,
        margin=dict(t=20, b=10, l=10, r=10),
        xaxis=dict(tickangle=-45),
        yaxis=dict(title="비중 (%)", range=[0, 100]),
        legend=dict(orientation="h", y=1.05, x=0),
    )
    st.plotly_chart(fig_cat, use_container_width=True)

    # 위험자산 비중 순 정렬 표
    cat_df_view = cat_df.sort_values("Risky", ascending=False).copy()
    cat_df_view = cat_df_view.round(1)
    cat_df_view = cat_df_view[["method", "Equity", "FixedIncome",
                               "RealAssets", "Cash", "Risky"]]
    st.dataframe(cat_df_view, hide_index=True, use_container_width=True, height=300)

st.markdown("---")

# ============================================================
# 4. ETF별 평균 비중 (21 모델)
# ============================================================
st.subheader("4. ETF별 평균 비중 (21개 모델 평균)")

if not df_pc.empty:
    avg = (df_pc[weight_cols].mean() * 100).round(2)
    avg_rows = pd.DataFrame({
        "ETF": [etf_label[s] for s in avg.index],
        "카테고리": [cat_of[s] for s in avg.index],
        "평균 비중 (%)": avg.values,
        "CIO 최종 (%)": [cio_w.get(s, 0.0) * 100 for s in avg.index],
    }).sort_values("평균 비중 (%)", ascending=False)

    c1, c2 = st.columns([3, 2])
    with c1:
        fig_avg = go.Figure()
        fig_avg.add_trace(go.Bar(
            y=avg_rows["ETF"], x=avg_rows["평균 비중 (%)"],
            orientation="h", name="21모델 평균",
            marker_color="#7e9bb8",
        ))
        fig_avg.add_trace(go.Bar(
            y=avg_rows["ETF"], x=avg_rows["CIO 최종 (%)"],
            orientation="h", name="CIO 최종",
            marker_color="#1f4e79",
        ))
        fig_avg.update_layout(
            barmode="group", height=420,
            margin=dict(t=20, b=10, l=10, r=10),
            xaxis=dict(title="비중 (%)"),
            yaxis=dict(autorange="reversed"),
            legend=dict(orientation="h", y=1.05, x=0),
        )
        st.plotly_chart(fig_avg, use_container_width=True)
    with c2:
        view = avg_rows.copy()
        view["평균 비중 (%)"] = view["평균 비중 (%)"].apply(lambda x: f"{x:.2f}")
        view["CIO 최종 (%)"] = view["CIO 최종 (%)"].apply(lambda x: f"{x:.2f}")
        st.dataframe(view, hide_index=True, use_container_width=True, height=420)

st.markdown("---")

# ============================================================
# 5. 모델 단일 선택 — 상세 비중
# ============================================================
st.subheader("5. 모델 상세 보기")

if not df_pc.empty:
    pick = st.selectbox(
        "모델 선택",
        options=df_pc["method"].tolist(),
        format_func=lambda m: f"{m} — {df_pc[df_pc['method']==m]['name'].iloc[0]}",
    )
    row = df_pc[df_pc["method"] == pick].iloc[0]
    detail = pd.DataFrame([
        {"ETF": etf_label[s], "카테고리": cat_of[s],
         "비중 (%)": row[s] * 100}
        for s in weight_cols
    ]).sort_values("비중 (%)", ascending=False)

    c1, c2 = st.columns([2, 3])
    with c1:
        # 도넛
        cats_pick = _category_totals({s: row[s] for s in weight_cols}, cat_of)
        fig_p = go.Figure(data=[go.Pie(
            labels=list(cats_pick.keys()),
            values=list(cats_pick.values()),
            hole=0.5,
            marker=dict(colors=[CATEGORY_COLORS[k] for k in cats_pick.keys()]),
            textinfo="label+percent",
            sort=False,
        )])
        fig_p.update_layout(height=320, margin=dict(t=20, b=10, l=10, r=10),
                            showlegend=False, title_text=f"{pick} 카테고리 비중")
        st.plotly_chart(fig_p, use_container_width=True)
    with c2:
        view2 = detail.copy()
        view2["비중 (%)"] = view2["비중 (%)"].apply(lambda x: f"{x:.2f}")
        st.dataframe(view2, hide_index=True, use_container_width=True, height=380)

st.markdown("---")

# ============================================================
# 6. CIO board memo (있으면)
# ============================================================
if board_memo_text:
    with st.expander("CIO Board Memo 펼쳐보기"):
        st.markdown(board_memo_text)

st.caption("Source: outputs_trimmed10/  |  ips_trimmed10.yaml (10 ETFs)")
