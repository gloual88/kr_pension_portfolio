"""
v2 Multi-Regime Architecture (KR / US / Global) — kr_pension_hybrid 결과.

이 페이지는 v0.3 score injection 결과를 시각화합니다:
  - KR / US / Global 3-regime 타임라인 (분기별)
  - 4-variant 백테스트 누적 비교 (v1, v2 baseline, v2 score, v2 Phase 2 LLM)
  - regime divergence 분기 (KR ≠ US) 하이라이트
  - score injection 효과 (자산별 CMA E[r] 차이)

데이터 소스: d:/파이선/kr_pension_hybrid/outputs/
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils import (
    render_sidebar,
    load_metrics, load_nav, load_weights, load_regime_history,
    VARIANT_LABELS, BT_V2_SCORE,
    HYBRID_OUTPUTS_DIR,
)


st.set_page_config(page_title="v2 Multi-Regime", page_icon=":globe_with_meridians:", layout="wide")
render_sidebar()

st.title("v2 Multi-Regime — KR / US / Global")
st.caption("v0.3 score injection 아키텍처 — 자산별 regime 매핑 + 연속 score 기반 CMA 조정")

# ============================================================
# 헤드라인 KPI — 4 variants
# ============================================================
st.subheader("백테스트 비교 (2018-Q1 ~ 2026-Q2, 34 quarters)")

variants = ["baseline", "v2_baseline", "v2_phase2", "v2_score"]
metrics = {v: load_metrics(v) for v in variants}

cols = st.columns(4)
ordered = [
    ("baseline",   "v1 baseline",      "#888888"),
    ("v2_baseline","v2 baseline",      "#2E86AB"),
    ("v2_phase2",  "v2 Phase 2 LLM",   "#E63946"),
    ("v2_score",   "v2 Score Injection ★", "#06A77D"),
]
for i, (v, label, color) in enumerate(ordered):
    with cols[i]:
        m = metrics[v]
        if m and "agentic" in m:
            a = m["agentic"]
            st.markdown(f"**{label}**")
            st.metric("Sharpe", f"{a.get('sharpe', 0):.3f}",
                       f"Ann ret {a.get('ann_return', 0)*100:.2f}%", delta_color="off")
            st.caption(f"MDD {a.get('max_drawdown', 0)*100:.2f}% / "
                        f"Total {a.get('total_return', 0)*100:.1f}%")
        else:
            st.warning(f"{label}: 데이터 없음")

st.markdown("---")

# ============================================================
# Cumulative NAV 4-variant 차트
# ============================================================
st.subheader("Cumulative NAV — 4 Variants")

fig = go.Figure()
for v, label, color in ordered:
    nav = load_nav(v)
    if nav is None:
        continue
    nav_idx = nav["agentic"] / nav["agentic"].iloc[0]
    fig.add_trace(go.Scatter(
        x=nav.index, y=nav_idx, name=label,
        line=dict(color=color, width=2 if v == "v2_score" else 1.5,
                  dash="solid" if v in ("v2_score", "baseline") else "dot"),
    ))

# 60/40 BM
nav_b = load_nav("baseline")
if nav_b is not None:
    bm_idx = nav_b["benchmark"] / nav_b["benchmark"].iloc[0]
    fig.add_trace(go.Scatter(
        x=nav_b.index, y=bm_idx, name="KR 60/40 BM",
        line=dict(color="#bbbbbb", width=1.2, dash="dash"),
    ))

fig.add_hline(y=1.0, line=dict(color="#cccccc", width=0.7))
fig.update_layout(
    height=420, margin=dict(t=20, b=10, l=10, r=10),
    xaxis_title=None, yaxis_title="NAV (Index = 1.0 at start)",
    legend=dict(orientation="h", y=1.05, x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ============================================================
# KR / US / Global Regime 타임라인
# ============================================================
st.subheader("KR / US / Global Regime 타임라인 (분기별)")

reg = load_regime_history("v2_score")
if reg is None or "regime_kr" not in reg.columns:
    # fallback: try v2_baseline
    reg = load_regime_history("v2_baseline")

if reg is not None and "regime_kr" in reg.columns:
    regime_colors = {
        "expansion":  "#06A77D",
        "late-cycle": "#F77F00",
        "recession":  "#E63946",
        "recovery":   "#118AB2",
    }
    fig = go.Figure()
    domains = [("regime_kr", "KR", 2), ("regime_us", "US", 1), ("regime_global", "Global", 0)]
    for col, name, y in domains:
        if col not in reg.columns:
            continue
        # Build segments — each row is a quarter
        for i, row in reg.iterrows():
            r = row.get(col)
            if pd.isna(r) or not r:
                continue
            t_start = pd.Timestamp(row["as_of"])
            t_end = pd.Timestamp(reg.iloc[i+1]["as_of"]) if i+1 < len(reg) else t_start + pd.DateOffset(months=3)
            color = regime_colors.get(r, "#cccccc")
            fig.add_shape(
                type="rect",
                x0=t_start, x1=t_end, y0=y-0.4, y1=y+0.4,
                fillcolor=color, line=dict(color=color, width=0),
                opacity=0.85,
            )
    # Divergence markers (KR != US)
    if "regime_us" in reg.columns:
        div = reg[reg["regime_kr"] != reg["regime_us"]]
        for _, row in div.iterrows():
            fig.add_shape(
                type="line",
                x0=row["as_of"], x1=row["as_of"], y0=-0.5, y1=2.5,
                line=dict(color="#222222", width=1.4, dash="dot"),
            )
    fig.update_layout(
        height=240, margin=dict(t=20, b=20, l=10, r=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(
            tickmode="array", tickvals=[0, 1, 2],
            ticktext=["Global", "US", "KR"],
            range=[-0.5, 2.5],
        ),
        showlegend=False,
    )
    # Legend manually via shapes (color blocks)
    st.plotly_chart(fig, use_container_width=True)
    legend_html = " &nbsp;|&nbsp; ".join(
        f"<span style='background:{c};padding:2px 8px;border-radius:3px;color:white;font-weight:bold;'>{r}</span>"
        for r, c in regime_colors.items()
    )
    st.markdown(legend_html + " &nbsp;&nbsp; <span style='color:#222'>┊┊┊</span> = KR ≠ US 발산 분기",
                 unsafe_allow_html=True)

    # Divergence table
    st.markdown("**Regime Divergence Quarters (KR ≠ US)**")
    if "regime_us" in reg.columns:
        div = reg[reg["regime_kr"] != reg["regime_us"]][["as_of", "regime_kr", "regime_us", "regime_global"]]
        div.columns = ["분기", "KR", "US", "Global"]
        st.dataframe(div, hide_index=True, use_container_width=True)
        st.caption(f"발산 분기 {len(div)}/{len(reg)} ({len(div)/len(reg)*100:.0f}%) — "
                    "v2 구조에서만 검출 가능. v1은 KR regime만 봤기에 미국 자산을 잘못 분류했음.")
else:
    st.info("v2 regime history 데이터 없음. backtest_walk_forward_kr 실행 필요.")

st.markdown("---")

# ============================================================
# Score Injection 효과 — v2_baseline vs v2_score 비중 비교
# ============================================================
st.subheader("Score Injection 효과 — Equity 비중 시계열")

w_base = load_weights("v2_baseline")
w_score = load_weights("v2_score")

if w_base is not None and w_score is not None:
    eq_cols = ["kr-large-cap", "kr-kosdaq", "kr-dividend",
               "us-large-cap", "us-tech", "us-dividend",
               "intl-developed", "emerging-markets"]
    eq_base = w_base[[c for c in eq_cols if c in w_base.columns]].sum(axis=1) * 100
    eq_score = w_score[[c for c in eq_cols if c in w_score.columns]].sum(axis=1) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eq_base.index, y=eq_base, name="v2 baseline (label)",
                              line=dict(color="#2E86AB", width=2), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=eq_score.index, y=eq_score, name="v2 score injection",
                              line=dict(color="#06A77D", width=2), mode="lines+markers"))
    fig.update_layout(
        height=350, margin=dict(t=20, b=10, l=10, r=10),
        xaxis_title=None, yaxis_title="Equity Weight (%)",
        legend=dict(orientation="h", y=1.05, x=0),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Score injection은 같은 regime 라벨 안에서도 매크로 score 차이 반영 → 분기마다 미세하게 다른 결정. "
                "특히 KR이 strong growth + late-cycle인 시기엔 equity 비중을 더 높게 유지.")
else:
    st.info("v2 baseline 또는 v2 score 비중 데이터 없음.")

st.markdown("---")

# ============================================================
# Score 주입 공식 + v0.3 결과 요약
# ============================================================
st.subheader("v0.3 Score Injection 공식")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Equity adjustment**")
    st.code(
        "adj = +0.020·growth\n"
        "    + 0.010·(-inflation)\n"
        "    + 0.015·monetary\n"
        "    + 0.010·financial",
        language="python",
    )
with col2:
    st.markdown("**Non-Equity (FI / Real / Cash)**")
    st.code(
        "adj = -0.010·growth\n"
        "    - 0.005·inflation\n"
        "    + 0.010·monetary\n"
        "    - 0.005·financial",
        language="python",
    )

st.markdown(
    "**핵심 인사이트**: 같은 \"late-cycle\"이라도 매크로 score 차이로 다른 처리.\n"
    "- KR (growth +0.66, inflation +0.69, monetary -0.49, financial -0.25): equity adj **-0.35%** (강한 growth가 인플레/긴축 상쇄)\n"
    "- US (growth +0.01, inflation +0.82, monetary -0.59, financial +0.19): equity adj **-1.49%** (성장 약함)\n"
    "- 라벨로는 둘 다 일률적 -2.00% 적용했던 것"
)

# ============================================================
# Footer
# ============================================================
st.markdown("---")
st.caption(
    "Production 권장: **v2 Score Injection** (Sharpe 1.152, 비용 \\$0). "
    "v2 Phase 2 LLM(\\$15) 폐기, v1/v2 baseline 후순위. "
    "상세: `kr_pension_hybrid/COMPARISON_v0.3_FINAL.md`"
)
