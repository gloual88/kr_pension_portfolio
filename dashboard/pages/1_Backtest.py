"""
Walk-Forward 백테스트 결과 상세.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# Allow `from utils import ...` when Streamlit launches from dashboard/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import (
    load_metrics, load_nav, load_weights, load_regime_history,
    compute_drawdown, render_sidebar, available_variants, VARIANT_LABELS,
    asset_class_meta, category_of, CATEGORY_COLORS,
)


st.set_page_config(page_title="백테스트 — KR 연금", layout="wide")
render_sidebar()

st.title("Walk-Forward 백테스트")

# 변형 선택 — 사용 가능한 variants만
avail = available_variants()
if not avail:
    st.error("백테스트 결과 없음. baseline부터 실행하세요.")
    st.stop()
variant = st.radio(
    "변형 선택",
    options=avail,
    format_func=lambda v: VARIANT_LABELS.get(v, v),
    horizontal=True,
    help="baseline: 결정적 매핑 / llm: Claude CIO 선택자 / llm_phase2: Claude CIO + CMA judge",
)

metrics = load_metrics(variant)
nav = load_nav(variant)
weights = load_weights(variant)
regime = load_regime_history(variant)

if metrics is None or nav is None:
    st.warning(f"`outputs/backtest_kr{'_llm' if variant == 'llm' else ''}/` 결과 없음. "
               f"다음을 실행하세요:\n\n"
               f"```\npython -m kr_pension_portfolio.scripts.backtest_walk_forward_kr "
               f"--variant {variant} --start 2018-01-01\n```")
    st.stop()

# ============================================================
# KPI 비교 표
# ============================================================
st.subheader("성과 요약")

a = metrics["agentic"]
b = metrics["benchmark_kr_60_40"]
df_kpi = pd.DataFrame({
    "지표": ["연환산 수익률", "연환산 변동성", "Sharpe Ratio",
            "Max Drawdown", "총 누적 수익률"],
    "Agentic SAA": [
        f"{a['ann_return']*100:.2f}%",
        f"{a['ann_vol']*100:.2f}%",
        f"{a['sharpe']:.3f}",
        f"{a['max_drawdown']*100:.2f}%",
        f"{a['total_return']*100:.2f}%",
    ],
    "KR 60/40 BM": [
        f"{b['ann_return']*100:.2f}%",
        f"{b['ann_vol']*100:.2f}%",
        f"{b['sharpe']:.3f}",
        f"{b['max_drawdown']*100:.2f}%",
        f"{b['total_return']*100:.2f}%",
    ],
    "차이 (Agentic − BM)": [
        f"{(a['ann_return']-b['ann_return'])*100:+.2f}%p",
        f"{(a['ann_vol']-b['ann_vol'])*100:+.2f}%p",
        f"{a['sharpe']-b['sharpe']:+.3f}",
        f"{(a['max_drawdown']-b['max_drawdown'])*100:+.2f}%p",
        f"{(a['total_return']-b['total_return'])*100:+.2f}%p",
    ],
})
st.dataframe(df_kpi, hide_index=True, use_container_width=True)

st.caption(f"분기 수: {metrics['n_rebalances']}, "
           f"평균 turnover/리밸런싱: {metrics['avg_turnover_per_rebal']*100:.2f}%, "
           f"총 비용: {metrics['total_cost']*10000:.1f}bp (5bp 가정)")

st.markdown("---")

# ============================================================
# NAV + Drawdown 차트
# ============================================================
st.subheader("NAV 추이")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=nav.index, y=nav["agentic"], name=f"Agentic SAA ({variant})",
    line=dict(color="#1f4e79", width=2),
))
fig.add_trace(go.Scatter(
    x=nav.index, y=nav["benchmark"], name="KR 60/40 BM",
    line=dict(color="#a8a8a8", width=1.5, dash="dash"),
))
fig.update_layout(
    height=380, margin=dict(t=20, b=10, l=10, r=10),
    yaxis_title="NAV (start = 1.0)",
    legend=dict(orientation="h", y=1.02, x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Drawdown")
dd_a = compute_drawdown(nav["agentic"])
dd_b = compute_drawdown(nav["benchmark"])
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=dd_a.index, y=dd_a*100, name=f"Agentic ({variant})",
    line=dict(color="#1f4e79", width=2), fill="tozeroy",
))
fig.add_trace(go.Scatter(
    x=dd_b.index, y=dd_b*100, name="KR 60/40 BM",
    line=dict(color="#a8a8a8", width=1.5, dash="dash"),
))
fig.update_layout(
    height=300, margin=dict(t=20, b=10, l=10, r=10),
    yaxis_title="Drawdown (%)",
    legend=dict(orientation="h", y=1.02, x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ============================================================
# 분기별 weights 히트맵
# ============================================================
st.subheader("분기별 자산군 비중 (Heatmap)")

if weights is not None and not weights.empty:
    # category 순으로 컬럼 재정렬
    meta = asset_class_meta()
    cat_order = ["Equity", "FixedIncome", "RealAssets", "Cash"]
    sorted_slugs = sorted(
        weights.columns,
        key=lambda s: (cat_order.index(category_of(s)) if category_of(s) in cat_order else 99, s),
    )
    w = weights[sorted_slugs]

    fig = go.Figure(data=go.Heatmap(
        z=w.values * 100,
        x=w.columns,
        y=[d.strftime("%Y-%m") for d in w.index],
        colorscale="Blues",
        zmin=0, zmax=max(20.0, w.values.max() * 100),
        colorbar=dict(title="비중 %"),
        hovertemplate="분기: %{y}<br>자산군: %{x}<br>비중: %{z:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        height=max(280, 24 * len(w) + 120),
        margin=dict(t=20, b=80, l=80, r=10),
        xaxis=dict(tickangle=-40, side="bottom"),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("weights_quarterly.csv 부재.")

st.markdown("---")

# ============================================================
# Regime + Ensemble 타임라인
# ============================================================
st.subheader("Regime / Ensemble 타임라인")

if regime is not None and not regime.empty:
    df = regime.copy()
    df["as_of"] = pd.to_datetime(df["as_of"])
    # 분기말까지 색상 stripe
    df["end"] = df["as_of"].shift(-1)
    df.loc[df["end"].isna(), "end"] = df["as_of"].iloc[-1] + pd.DateOffset(months=3)

    REGIME_COLORS = {
        "expansion":   "#5b8a72",
        "late-cycle":  "#c89b3c",
        "recession":   "#a04545",
        "recovery":    "#7e9bb8",
    }

    fig = go.Figure()
    for _, row in df.iterrows():
        fig.add_shape(
            type="rect",
            x0=row["as_of"], x1=row["end"],
            y0=0, y1=1,
            fillcolor=REGIME_COLORS.get(row["regime"], "#cccccc"),
            opacity=0.65, line_width=0,
        )
        fig.add_annotation(
            x=row["as_of"] + (row["end"] - row["as_of"]) / 2,
            y=0.5, text=row["ensemble"][:14],
            showarrow=False, font=dict(size=9, color="white"),
        )
    fig.update_layout(
        height=140, margin=dict(t=30, b=30, l=10, r=10),
        xaxis=dict(range=[df["as_of"].min(), df["end"].max()]),
        yaxis=dict(visible=False, range=[0, 1]),
        showlegend=False,
        title="레짐 색상: 녹(expansion) / 황(late-cycle) / 적(recession) / 청(recovery). 라벨: 선택된 앙상블",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("분기별 상세")
    df_show = regime.copy()
    df_show["as_of"] = df_show["as_of"].dt.strftime("%Y-%m-%d")
    df_show["regime_conf"] = df_show["regime_conf"].apply(lambda x: f"{x:.2f}")
    df_show["p_rec"] = df_show["p_rec"].apply(lambda x: f"{x*100:.0f}%")
    df_show.columns = ["분기", "레짐", "신뢰도", "12m 침체확률", "선택된 앙상블"]
    st.dataframe(df_show, hide_index=True, use_container_width=True, height=320)
else:
    st.info("regime_history.csv 부재.")
