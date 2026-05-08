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
    load_variant_current_cio, load_variant_current_macro, load_variant_board_memo,
    VARIANT_LABELS, BT_V2_SCORE,
    HYBRID_OUTPUTS_DIR,
    CATEGORY_COLORS, category_of, category_totals, display_name, risk_asset_weight,
)


st.set_page_config(page_title="v2 Multi-Regime", page_icon=":globe_with_meridians:", layout="wide")
render_sidebar()

st.title("v2 Multi-Regime — KR / US / Global")
st.caption("v0.3 score injection 아키텍처 — 자산별 regime 매핑 + 연속 score 기반 CMA 조정")

# ============================================================
# 현재 추천 포트폴리오 (v2 score 단일 시점)
# ============================================================
st.subheader("현재 추천 포트폴리오 — v2 Score Injection (Production ★)")

cio_v2 = load_variant_current_cio("v2_score")
macro_v2 = load_variant_current_macro("v2_score")

if cio_v2 is None or macro_v2 is None:
    st.warning(
        "v2 score 단일시점 결과 없음. `kr_pension_hybrid/run_pipeline.py` 실행 후 "
        "outputs/run_v2_score/cio/, macro/ 를 outputs/v2_score/cio/, macro/ 로 복사."
    )
else:
    weights = cio_v2["weights"]
    regimes = macro_v2.get("regimes", {})
    risk_w = risk_asset_weight(weights)
    cat_totals = category_totals(weights)
    m = cio_v2.get("metrics", {})

    # 4-regime KPI bar
    kr = regimes.get("kr", {}); us = regimes.get("us", {}); gl = regimes.get("global", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("위험자산 비중", f"{risk_w*100:.1f}%",
                   f"한도 70% — 여유 {(0.70-risk_w)*100:.1f}%p",
                   delta_color="normal" if risk_w <= 0.70 else "inverse")
    with c2:
        st.metric("KR Regime", kr.get("regime", "?"),
                   f"신뢰도 {kr.get('confidence', 0):.2f} | P(rec) {kr.get('recession_probability_12m', 0)*100:.0f}%",
                   delta_color="off")
    with c3:
        st.metric("US Regime", us.get("regime", "?"),
                   f"신뢰도 {us.get('confidence', 0):.2f} | P(rec) {us.get('recession_probability_12m', 0)*100:.0f}%",
                   delta_color="off")
    with c4:
        st.metric("Global Regime", gl.get("regime", "?"),
                   f"신뢰도 {gl.get('confidence', 0):.2f}",
                   delta_color="off")

    st.markdown(f"**선택 앙상블:** `{cio_v2.get('chosen_ensemble', '?')}` — "
                 f"E[r] {m.get('expected_return', 0)*100:.2f}% / "
                 f"σ {m.get('expected_vol', 0)*100:.2f}% / "
                 f"BT Sharpe {m.get('backtest_sharpe', 0):.2f}")

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**카테고리별 비중**")
        fig = go.Figure(data=[go.Pie(
            labels=list(cat_totals.keys()),
            values=list(cat_totals.values()),
            hole=0.45,
            marker=dict(colors=[CATEGORY_COLORS[k] for k in cat_totals.keys()]),
            textinfo="label+percent",
            textposition="outside",
            sort=False,
        )])
        fig.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10),
                           showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("**Top 10 비중 (regime domain 표시)**")
        rows = []
        for slug, w in weights.items():
            from utils import asset_class_meta
            meta = asset_class_meta().get(slug, {})
            rows.append({
                "ETF": display_name(slug),
                "카테고리": category_of(slug),
                "비중": w,
            })
        df = pd.DataFrame(rows).sort_values("비중", ascending=False).head(10)
        df["비중"] = df["비중"].apply(lambda x: f"{x*100:.2f}%")
        st.dataframe(df, hide_index=True, use_container_width=True, height=350)

    with st.expander("Board Memo (CIO 의사결정 메모)"):
        memo = load_variant_board_memo("v2_score")
        st.markdown(memo or "_Board memo 없음_")

st.markdown("---")

# ============================================================
# 헤드라인 KPI — 4 variants
# ============================================================
st.subheader("백테스트 비교 (2018-Q1 ~ 2026-Q2, 34 quarters)")

variants = ["baseline", "v2_score", "v2_score_aggressive", "v2_score_aggressive_pcr"]
metrics = {v: load_metrics(v) for v in variants}

cols = st.columns(4)
ordered = [
    ("baseline",   "v1 baseline",      "#888888"),
    ("v2_score",   "v0.3 score injection", "#06A77D"),
    ("v2_score_aggressive", "v0.5 aggressive IPS", "#D62828"),
    ("v2_score_aggressive_pcr", "v0.5.1 PC re-weight ★", "#9D4EDD"),
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
    is_prod = v == "v2_score_aggressive_pcr"
    fig.add_trace(go.Scatter(
        x=nav.index, y=nav_idx, name=label,
        line=dict(color=color, width=2.4 if is_prod else 1.5,
                  dash="solid" if v in ("v2_score_aggressive_pcr", "baseline") else "dot"),
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
# v0.5.1 — PC Ensemble Re-weighting (return-seek tilt)
# ============================================================
st.subheader("v0.5.1 — PC Ensemble Re-weighting (return-seek tilt)")

m_v05 = load_metrics("v2_score_aggressive")
m_v051 = load_metrics("v2_score_aggressive_pcr")

if m_v05 and m_v051:
    a05 = m_v05.get("agentic", {})
    a051 = m_v051.get("agentic", {})

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**v0.5 (적극 IPS)**")
        st.write(f"- PC ensemble: `inverse_te` (BM TE 역수, risk-min 편향)")
        st.write(f"- Sharpe: **{a05.get('sharpe', 0):.3f}**")
        st.write(f"- Annual Return: {a05.get('ann_return', 0)*100:.2f}%")
        st.write(f"- Total Return: {a05.get('total_return', 0)*100:.1f}%")
        st.write(f"- σ: {a05.get('ann_vol', 0)*100:.2f}% / MDD {a05.get('max_drawdown', 0)*100:.2f}%")
    with col_b:
        st.markdown("**v0.5.1 (PC re-weight) ★**")
        st.write(f"- PC ensemble: `regime_conditional` (return-seek 적극 테이블)")
        st.write(f"- Sharpe: **{a051.get('sharpe', 0):.3f}** (+{(a051.get('sharpe', 0)-a05.get('sharpe', 0)):.3f})")
        st.write(f"- Annual Return: **{a051.get('ann_return', 0)*100:.2f}%** (+{(a051.get('ann_return', 0)-a05.get('ann_return', 0))*100:.2f}pp)")
        st.write(f"- Total Return: **{a051.get('total_return', 0)*100:.1f}%** (+{(a051.get('total_return', 0)-a05.get('total_return', 0))*100:.1f}pp)")
        st.write(f"- σ {a051.get('ann_vol', 0)*100:.2f}% / MDD {a051.get('max_drawdown', 0)*100:.2f}% (동일)")

    st.success(
        "**v0.5.1 변경 핵심**: PC ensemble 가중치 재설계. "
        "late-cycle에서 max_sharpe ×2.0, BL ×1.8, mean_downside ×1.5로 boost, "
        "inverse_volatility/min_correlation/gmv는 ×0.4로 down-weight. "
        "MDD 변화 없이 추가 +0.17pp 수익 확보. "
        "v0.3 → v0.5.1 누적 효과: **Sharpe +3.3%, Total Return +36% 가속.**"
    )
else:
    st.warning("v0.5.1 비교 데이터 없음.")

st.markdown("---")

# ============================================================
# v0.5 — IPS 적극화 (변동성 band + risky 하한)
# ============================================================
st.subheader("v0.5 — IPS 적극화 적용 결과")

m_v03 = load_metrics("v2_score")
m_v05 = load_metrics("v2_score_aggressive")

if m_v03 and m_v05:
    a03 = m_v03.get("agentic", {})
    a05 = m_v05.get("agentic", {})

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**v0.3 (보수 IPS)**")
        st.write(f"- IPS: σ band [6%, 12%], risky 하한 0%")
        st.write(f"- Sharpe: **{a03.get('sharpe', 0):.3f}**")
        st.write(f"- Annual Return: {a03.get('ann_return', 0)*100:.2f}%")
        st.write(f"- Annual Vol: **{a03.get('ann_vol', 0)*100:.2f}%** (하한 6% 미달)")
        st.write(f"- Total Return: {a03.get('total_return', 0)*100:.1f}%")
    with col_b:
        st.markdown("**v0.5 (적극 IPS) ★**")
        st.write(f"- IPS: σ band [**8%, 14%**], risky 하한 **40%**")
        st.write(f"- Sharpe: **{a05.get('sharpe', 0):.3f}** (+{(a05.get('sharpe', 0)-a03.get('sharpe', 0)):.3f})")
        st.write(f"- Annual Return: **{a05.get('ann_return', 0)*100:.2f}%** (+{(a05.get('ann_return', 0)-a03.get('ann_return', 0))*100:.2f}pp)")
        st.write(f"- Annual Vol: {a05.get('ann_vol', 0)*100:.2f}%")
        st.write(f"- Total Return: **{a05.get('total_return', 0)*100:.1f}%** (+{(a05.get('total_return', 0)-a03.get('total_return', 0))*100:.1f}pp)")

    st.success(
        "**v0.5 IPS 적극화 효과**: 변동성 band 6%→8% 상향 + Equity 하한 35% / RealAssets 5% / Cash 천장 20%. "
        "이는 모델이 강제로 위험자산 40% 이상 보유하게 만듦 → 2018-2026 강세장 참여 확대. "
        "BM Sharpe 1.310과의 격차 0.158 → 0.128로 19% 축소. "
        "남은 격차는 PC ensemble 가중 조정 (v0.5.1)으로 추가 해소 가능."
    )
else:
    st.warning("v0.5 비교 데이터 없음.")

st.markdown("---")

# ============================================================
# v0.4.1 — Benchmark 재정의 (KR 60/40 → 글로벌 분산)
# ============================================================
st.subheader("v0.4.1 — Benchmark 재정의 (KR 60/40 → 글로벌 분산)")

m_kr_bm = load_metrics("v2_score")
m_global_bm = load_metrics("v2_score_globalbm")

if m_kr_bm and m_global_bm:
    bm_kr = m_kr_bm.get("benchmark_kr_60_40", {})
    bm_gl = m_global_bm.get("benchmark_kr_60_40", {})
    ag_kr = m_kr_bm.get("agentic", {})
    ag_gl = m_global_bm.get("agentic", {})

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**구 BM — KR 60/40 (KOSPI200 60% + KTB10Y 40%)**")
        st.write(f"- Annual Return: **{bm_kr.get('ann_return', 0)*100:.2f}%**")
        st.write(f"- Annual Vol: **{bm_kr.get('ann_vol', 0)*100:.2f}%**")
        st.write(f"- Sharpe: **{bm_kr.get('sharpe', 0):.3f}**")
        st.write(f"- MDD: **{bm_kr.get('max_drawdown', 0)*100:.2f}%**")
        st.write(f"- TE (vs Agentic): **8.62%** (budget 6% 초과)")
    with col_b:
        st.markdown("**신 BM — 글로벌 분산 (KR30 + US30 + Bond40) ★**")
        st.write(f"- Annual Return: **{bm_gl.get('ann_return', 0)*100:.2f}%**")
        st.write(f"- Annual Vol: **{bm_gl.get('ann_vol', 0)*100:.2f}%** (-30% vs 구 BM)")
        st.write(f"- Sharpe: **{bm_gl.get('sharpe', 0):.3f}** (+41% vs 구 BM)")
        st.write(f"- MDD: **{bm_gl.get('max_drawdown', 0)*100:.2f}%** (+29% 개선)")
        st.write(f"- TE (vs Agentic): **5.06%** (budget 6% 이내 ✓)")

    st.info(
        "**의외의 발견**: 글로벌 분산 BM 자체가 매우 효율적 — Sharpe 1.310. "
        f"v2 score Agentic Sharpe **{ag_gl.get('sharpe', 0):.3f}**이 BM보다 낮음. "
        "이는 v2 score 모델이 risky 35% (보수)인 반면 BM은 60% (적극)이기 때문. "
        "2018-2026 강세장에서 위험 부담 적은 모델은 BM 못 따라감. "
        "**다음 v0.5 후보**: IPS 변동성 band 재조정, equity 하한 설정."
    )
else:
    st.warning("v0.4.1 BM 비교 데이터 미완. 백테스트 재실행 필요.")

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
