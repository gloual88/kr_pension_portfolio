"""
Variant 비교 — Baseline / Phase 1 (CIO LLM) / Phase 2 (CIO + CMA LLM).

각 변형의 결과 디렉토리 존재 여부에 따라 자동으로 2-way 또는 3-way 비교를
표시합니다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import (
    load_metrics, load_nav, load_regime_history,
    compute_drawdown, render_sidebar,
    available_variants, VARIANT_LABELS, VARIANT_DIRS,
)


st.set_page_config(page_title="Variants 비교 — KR 연금", layout="wide")
render_sidebar()

st.title("Variants 비교: Baseline / Phase 1 / Phase 2")
st.caption("동일 IPS, 매크로 panel, PC engine — 차이는 LLM 사용 범위만")

# 색상 매핑
COLORS = {
    "baseline":   "#7e9bb8",
    "llm":        "#1f4e79",
    "llm_phase2": "#a04545",
    "benchmark":  "#a8a8a8",
}

avail = available_variants()
if not avail:
    st.error("아무 백테스트도 실행되지 않았습니다.")
    st.code(
        "& \"d:\\파이선\\pykrx_venv\\Scripts\\python.exe\" -m "
        "kr_pension_portfolio.scripts.backtest_walk_forward_kr "
        "--variant baseline --start 2018-01-01",
        language="powershell",
    )
    st.stop()

# 안내 — 누락된 variant
ALL_VARIANTS = ["baseline", "llm", "llm_phase2"]
missing = [v for v in ALL_VARIANTS if v not in avail]
if missing:
    st.info(
        "**미실행 variants:** " + ", ".join(VARIANT_LABELS[v] for v in missing) +
        "\n\n실행 명령:\n```powershell\n" +
        "\n".join(
            f"& \"d:\\파이선\\pykrx_venv\\Scripts\\python.exe\" -m "
            f"kr_pension_portfolio.scripts.backtest_walk_forward_kr "
            f"--variant {v} --start 2018-01-01"
            for v in missing
        ) + "\n```"
    )

# ============================================================
# 성과 비교 표 (가로 — variant별 컬럼)
# ============================================================
st.subheader("성과 비교 표")

metrics_dict = {v: load_metrics(v) for v in avail}
bm_metrics = metrics_dict[avail[0]]["benchmark_kr_60_40"]

rows = []
KPI_DEFS = [
    ("연환산 수익률", "ann_return", True),
    ("연환산 변동성", "ann_vol", True),
    ("Sharpe", "sharpe", False),
    ("Max Drawdown", "max_drawdown", True),
    ("총 누적 수익률", "total_return", True),
]

# 행: 지표, 열: 각 variant + BM
for label, key, is_pct in KPI_DEFS:
    row = {"지표": label}
    for v in avail:
        val = metrics_dict[v]["agentic"][key]
        row[VARIANT_LABELS[v]] = (f"{val*100:.2f}%" if is_pct else f"{val:.3f}")
    bv = bm_metrics[key]
    row["KR 60/40 BM"] = (f"{bv*100:.2f}%" if is_pct else f"{bv:.3f}")
    rows.append(row)

# 추가 행 — 분기 수, turnover
for label, key in [("분기 수", "n_rebalances"),
                   ("평균 turnover/리밸", "avg_turnover_per_rebal")]:
    row = {"지표": label}
    for v in avail:
        val = metrics_dict[v].get(key, 0)
        if "turnover" in key:
            row[VARIANT_LABELS[v]] = f"{val*100:.2f}%"
        else:
            row[VARIANT_LABELS[v]] = str(val)
    row["KR 60/40 BM"] = "-"
    rows.append(row)

st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# 승자 강조
if len(avail) >= 2:
    sharpe_vals = {v: metrics_dict[v]["agentic"]["sharpe"] for v in avail}
    mdd_vals = {v: metrics_dict[v]["agentic"]["max_drawdown"] for v in avail}
    ret_vals = {v: metrics_dict[v]["agentic"]["total_return"] for v in avail}
    sharpe_winner = max(sharpe_vals, key=sharpe_vals.get)
    mdd_winner = max(mdd_vals, key=mdd_vals.get)  # closer to 0 = better
    ret_winner = max(ret_vals, key=ret_vals.get)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Sharpe 승자", VARIANT_LABELS[sharpe_winner],
                  f"{sharpe_vals[sharpe_winner]:.3f}")
    with c2:
        st.metric("MDD 회피 승자", VARIANT_LABELS[mdd_winner],
                  f"{mdd_vals[mdd_winner]*100:.2f}%")
    with c3:
        st.metric("총 수익률 승자", VARIANT_LABELS[ret_winner],
                  f"{ret_vals[ret_winner]*100:.2f}%")

st.markdown("---")

# ============================================================
# NAV 비교
# ============================================================
st.subheader("NAV 추이 비교")

fig = go.Figure()
nav_dict = {v: load_nav(v) for v in avail}
ref_bm_nav = None
for v in avail:
    nv = nav_dict[v]
    if nv is None:
        continue
    fig.add_trace(go.Scatter(
        x=nv.index, y=nv["agentic"], name=VARIANT_LABELS[v],
        line=dict(color=COLORS.get(v, "#444"), width=2.0),
    ))
    if ref_bm_nav is None:
        ref_bm_nav = nv["benchmark"]
        bm_index = nv.index

if ref_bm_nav is not None:
    fig.add_trace(go.Scatter(
        x=bm_index, y=ref_bm_nav, name="KR 60/40 BM",
        line=dict(color=COLORS["benchmark"], width=1.4, dash="dash"),
    ))

fig.update_layout(
    height=400, margin=dict(t=20, b=10, l=10, r=10),
    yaxis_title="NAV (start = 1.0)",
    legend=dict(orientation="h", y=1.02, x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ============================================================
# Drawdown 비교
# ============================================================
st.subheader("Drawdown 비교")

fig = go.Figure()
for v in avail:
    nv = nav_dict[v]
    if nv is None:
        continue
    dd = compute_drawdown(nv["agentic"])
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd*100, name=VARIANT_LABELS[v],
        line=dict(color=COLORS.get(v, "#444"), width=2.0),
    ))
if ref_bm_nav is not None:
    dd_bm = compute_drawdown(ref_bm_nav)
    fig.add_trace(go.Scatter(
        x=dd_bm.index, y=dd_bm*100, name="KR 60/40 BM",
        line=dict(color=COLORS["benchmark"], width=1.4, dash="dash"),
    ))

fig.update_layout(
    height=320, margin=dict(t=20, b=10, l=10, r=10),
    yaxis_title="Drawdown (%)",
    legend=dict(orientation="h", y=1.02, x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ============================================================
# 누적 alpha 시계열 (vs baseline)
# ============================================================
if len(avail) >= 2 and "baseline" in avail:
    st.subheader("누적 NAV 격차 (vs Baseline)")
    base_nav = nav_dict["baseline"]
    if base_nav is not None:
        fig = go.Figure()
        for v in avail:
            if v == "baseline":
                continue
            nv = nav_dict[v]
            if nv is None:
                continue
            # 합집합 인덱스
            joined = base_nav[["agentic"]].rename(columns={"agentic": "base"}).join(
                nv[["agentic"]].rename(columns={"agentic": "var"}), how="inner"
            )
            diff = (joined["var"] - joined["base"]) * 100  # %p
            fig.add_trace(go.Scatter(
                x=diff.index, y=diff, name=f"{VARIANT_LABELS[v]} − Baseline",
                line=dict(color=COLORS.get(v, "#444"), width=2.0),
                fill="tozeroy", opacity=0.4,
            ))
        fig.add_hline(y=0, line_dash="dash", line_color="#888")
        fig.update_layout(
            height=300, margin=dict(t=20, b=10, l=10, r=10),
            yaxis_title="NAV 차이 (%p, baseline 대비)",
            legend=dict(orientation="h", y=1.02, x=0),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("양수 = baseline 대비 outperform. 누적 격차의 시점별 발생 양상 확인용.")

st.markdown("---")

# ============================================================
# 분기별 ensemble 선택 비교
# ============================================================
st.subheader("분기별 Ensemble 선택")

regime_dict = {v: load_regime_history(v) for v in avail}
all_have_regime = all(r is not None for r in regime_dict.values())

if all_have_regime:
    # 일치율 매트릭스
    if len(avail) >= 2:
        st.markdown("**일치율 매트릭스** (분기별 같은 ensemble 선택 비율)")
        match_rows = []
        for v1 in avail:
            row = {"variant": VARIANT_LABELS[v1]}
            for v2 in avail:
                if v1 == v2:
                    row[VARIANT_LABELS[v2]] = "—"
                else:
                    df = pd.merge(
                        regime_dict[v1][["as_of", "ensemble"]],
                        regime_dict[v2][["as_of", "ensemble"]],
                        on="as_of", suffixes=("_1", "_2"),
                    )
                    if len(df):
                        m = (df["ensemble_1"] == df["ensemble_2"]).sum()
                        row[VARIANT_LABELS[v2]] = f"{m}/{len(df)} ({m/len(df)*100:.0f}%)"
                    else:
                        row[VARIANT_LABELS[v2]] = "-"
            match_rows.append(row)
        st.dataframe(pd.DataFrame(match_rows), hide_index=True, use_container_width=True)

    # ensemble 빈도 비교
    st.markdown("**Ensemble 사용 빈도**")
    freq_data = {}
    for v in avail:
        freq_data[VARIANT_LABELS[v]] = regime_dict[v]["ensemble"].value_counts()
    freq = pd.DataFrame(freq_data).fillna(0).astype(int)
    freq = freq.sort_values(freq.columns[0], ascending=False)
    st.dataframe(freq, use_container_width=True)
