"""
KR 연금 자율주행 SAA 대시보드 — 개요 (Home).

페이지 목록:
  1. 개요 (이 파일)
  2. 백테스트 (Walk-Forward 결과)
  3. 매크로 / Regime
  4. 자산군 분석
  5. Baseline vs LLM 비교
  6. 현재 포트폴리오
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils import (
    load_json, load_metrics, load_nav,
    CIO_FILE, MACRO_FILE, CATEGORY_COLORS,
    asset_class_meta, category_of, display_name,
    category_totals, risk_asset_weight,
    render_sidebar,
)


st.set_page_config(
    page_title="KR 연금 자율주행 SAA",
    page_icon=":robot_face:",
    layout="wide",
)

render_sidebar()

st.title("KR 연금 자율주행 SAA — 대시보드")
st.caption("Andrew Ang 2026 reverse 구현 + ECOS/FRED 매크로 + DC/IRP 70% 한도 + v2 Multi-Regime (KR/US/Global) + Score Injection")

# v2 production highlight (latest = v0.5 aggressive)
v2_score_aggr = load_metrics("v2_score_aggressive")
v2_score_metrics = load_metrics("v2_score")
if v2_score_aggr and "agentic" in v2_score_aggr:
    a = v2_score_aggr["agentic"]
    st.success(
        f"🥇 **v0.5 Aggressive IPS 적용 중** — Walk-Forward Sharpe **{a['sharpe']:.3f}** "
        f"(v1 baseline 1.117 대비 +{(a['sharpe']-1.117)*100/1.117:.1f}%) | "
        f"Annual Return {a['ann_return']*100:.2f}% / MDD {a['max_drawdown']*100:.2f}% / "
        f"Total **{a['total_return']*100:.1f}%** (v0.3 64% 대비 +20pp). "
        f"상세는 좌측 메뉴의 **v2 Multi-Regime** 페이지 참고."
    )
elif v2_score_metrics and "agentic" in v2_score_metrics:
    a = v2_score_metrics["agentic"]
    st.success(
        f"🥇 **v2 Score Injection 적용 중** — Walk-Forward Sharpe **{a['sharpe']:.3f}**"
    )

# ============================================================
# 데이터 로드
# ============================================================
cio = load_json(CIO_FILE)
macro = load_json(MACRO_FILE)
metrics = load_metrics("baseline")
nav = load_nav("baseline")

if cio is None or macro is None:
    st.error("`outputs/cio/final_portfolio.json` 또는 `outputs/macro/macro-view.json` 부재. "
             "단일시점 파이프라인을 먼저 실행하세요: "
             "`python -m kr_pension_portfolio.run_pipeline --data yfinance`")
    st.stop()

weights = cio["weights"]
chosen_ensemble = cio["chosen_ensemble"]
regime = macro["regime"]
confidence = macro["confidence"]
p_rec = macro["recession_probability_12m"]
m = cio["metrics"]

# ============================================================
# KPI 카드 (4개)
# ============================================================
risk_w = risk_asset_weight(weights)
ips_compliance = m.get("ips_compliance", 0.0)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(
        "현재 위험자산 비중",
        f"{risk_w*100:.1f}%",
        f"한도 70% — 여유 {(0.70-risk_w)*100:.1f}%p",
        delta_color="normal" if risk_w <= 0.70 else "inverse",
    )
with c2:
    st.metric(
        "거시 레짐",
        regime,
        f"신뢰도 {confidence:.2f} | 12m 침체확률 {p_rec*100:.0f}%",
        delta_color="off",
    )
with c3:
    st.metric(
        "단일시점 BT Sharpe",
        f"{m.get('backtest_sharpe', 0):.2f}",
        f"E[r] {m.get('expected_return', 0)*100:.2f}% / σ {m.get('expected_vol', 0)*100:.2f}%",
        delta_color="off",
    )
with c4:
    bm_sharpe = metrics.get("benchmark_kr_60_40", {}).get("sharpe", 0.0) if metrics else 0.0
    bt_sharpe = metrics.get("agentic", {}).get("sharpe", 0.0) if metrics else 0.0
    st.metric(
        "Walk-Forward Sharpe",
        f"{bt_sharpe:.2f}",
        f"vs KR 60/40 {bm_sharpe:.2f} ({(bt_sharpe-bm_sharpe):+.2f})" if metrics else "백테스트 결과 없음",
        delta_color="off",
    )

st.markdown(f"**선택된 앙상블:** `{chosen_ensemble}` — {cio.get('rationale', '')[:200]}")

st.markdown("---")

# ============================================================
# 자산 배분 시각화 (도넛 + Top 비중 표)
# ============================================================
left, right = st.columns([3, 2])

with left:
    st.subheader("카테고리별 비중 — 현재 추천")
    cat_totals = category_totals(weights)
    fig = go.Figure(data=[go.Pie(
        labels=list(cat_totals.keys()),
        values=list(cat_totals.values()),
        hole=0.45,
        marker=dict(colors=[CATEGORY_COLORS[k] for k in cat_totals.keys()]),
        textinfo="label+percent",
        textposition="outside",
        sort=False,
    )])
    fig.update_layout(
        height=380, margin=dict(t=10, b=10, l=10, r=10),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(f"DC/IRP 위험자산 한도: Equity + RealAssets = "
               f"{cat_totals['Equity']*100:.1f}% + {cat_totals['RealAssets']*100:.1f}% "
               f"= **{risk_w*100:.1f}%** (한도 70%)")

with right:
    st.subheader("자산군 비중 — Top 10")
    df = pd.DataFrame([
        {
            "자산군": display_name(slug),
            "카테고리": category_of(slug),
            "비중": w,
        }
        for slug, w in weights.items()
    ])
    df = df.sort_values("비중", ascending=False).head(10)
    df["비중"] = df["비중"].apply(lambda x: f"{x*100:.2f}%")
    st.dataframe(df, hide_index=True, use_container_width=True, height=380)

st.markdown("---")

# ============================================================
# 백테스트 NAV 미니 차트 + 요약 표
# ============================================================
if nav is not None:
    st.subheader("Walk-Forward NAV 추이 (baseline)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nav.index, y=nav["agentic"], name="Agentic SAA",
        line=dict(color="#1f4e79", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=nav.index, y=nav["benchmark"], name="KR 60/40 (KOSPI200/KTB10Y)",
        line=dict(color="#a8a8a8", width=1.5, dash="dash"),
    ))
    fig.update_layout(
        height=320, margin=dict(t=20, b=10, l=10, r=10),
        xaxis_title=None, yaxis_title="NAV (start = 1.0)",
        legend=dict(orientation="h", y=1.02, x=0),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    if metrics:
        c1, c2, c3 = st.columns(3)
        a = metrics["agentic"]
        b = metrics["benchmark_kr_60_40"]
        with c1:
            st.metric("Agentic Sharpe", f"{a['sharpe']:.3f}",
                      f"vs BM {b['sharpe']:.3f}", delta_color="off")
        with c2:
            st.metric("Agentic MDD", f"{a['max_drawdown']*100:.2f}%",
                      f"vs BM {b['max_drawdown']*100:.2f}%", delta_color="off")
        with c3:
            st.metric("Total Return", f"{a['total_return']*100:.2f}%",
                      f"vs BM {b['total_return']*100:.2f}%", delta_color="off")
        st.caption(f"백테스트 분기 수: {metrics['n_rebalances']}, "
                   f"총 turnover: {metrics['total_turnover']*100:.1f}%, "
                   f"총 비용: {metrics['total_cost']*10000:.1f}bp")
else:
    st.info("Walk-Forward 백테스트 결과 부재. 다음을 실행하세요:\n\n"
            "```\npython -m kr_pension_portfolio.scripts.backtest_walk_forward_kr "
            "--variant baseline --start 2018-01-01\n```")

st.markdown("---")

# ============================================================
# 페이지 가이드
# ============================================================
st.subheader("페이지 가이드")
guide = """
- **백테스트**: Walk-Forward NAV, Drawdown, 분기별 비중 히트맵, regime 타임라인
- **매크로 / Regime**: 14개 매크로 readings, regime 분류 점수
- **자산군 분석**: 18 ETF 별 CMA, 변동성, 시그널, 분석 메모
- **Baseline vs LLM**: stub 매핑 vs Claude (Phase 1) 비교 (LLM 백테스트 후)
- **현재 포트폴리오**: 기본 실행 결과의 최종 비중, 카테고리 합계, Board Memo
- **월간 연금 포트폴리오**: 10-ETF 축약 유니버스 + 21개 PC 모델 비중 + CIO 최종 추천
- **v2 Multi-Regime ★**: KR/US/Global 3-regime + score injection (production 추천)
"""
st.markdown(guide)
