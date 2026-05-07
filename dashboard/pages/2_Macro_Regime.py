"""
매크로 / Regime 분류 결과 시각화.

데이터 소스: outputs/macro/macro-view.json (MacroAgent 산출물).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import load_json, load_md, MACRO_FILE, OUTPUTS_DIR, render_sidebar


st.set_page_config(page_title="매크로 / Regime — KR 연금", layout="wide")
render_sidebar()

st.title("매크로 / Regime 분류")
st.caption("ECOS (BOK) 12개 + FRED 3개 매크로 readings → Andrew Ang 2026 reverse 매핑")

macro = load_json(MACRO_FILE)
if macro is None:
    st.error("`outputs/macro/macro-view.json` 부재. 단일시점 파이프라인을 먼저 실행하세요.")
    st.stop()

regime = macro["regime"]
confidence = macro["confidence"]
p_rec = macro["recession_probability_12m"]
scores = macro.get("scores", {})
readings = macro.get("readings", {})
provenance = macro.get("provenance", {})
notes = macro.get("notes", "")
curve_signal = macro.get("curve_signal", {})

# ============================================================
# 현재 Regime 카드 + 점수
# ============================================================
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("현재 Regime", regime, f"신뢰도 {confidence:.2f}")
with c2:
    st.metric("12개월 침체 확률", f"{p_rec*100:.0f}%",
              "위험 회피 강화" if p_rec >= 0.30 else "정상 범위")
with c3:
    if curve_signal:
        st.metric("수익률곡선 상태", curve_signal.get("regime", "n/a"),
                  f"{curve_signal.get('shape', 'n/a')} / {curve_signal.get('curve_change_20d_bp', 0):+.0f}bp")
    else:
        n_readings = sum(1 for k in readings if not k.startswith("_"))
        st.metric("Macro Readings 수", n_readings,
                  f"ECOS+FRED 자동 fetch")

st.markdown("---")

# ============================================================
# Regime 점수 막대 차트
# ============================================================
st.subheader("Regime 분류 점수")

if scores:
    df_scores = pd.DataFrame({
        "Regime": list(scores.keys()),
        "Score": list(scores.values()),
    }).sort_values("Score", ascending=True)

    REGIME_COLORS = {
        "expansion":   "#5b8a72",
        "late-cycle":  "#c89b3c",
        "recession":   "#a04545",
        "recovery":    "#7e9bb8",
    }
    df_scores["color"] = df_scores["Regime"].map(REGIME_COLORS).fillna("#999999")

    fig = go.Figure(go.Bar(
        x=df_scores["Score"], y=df_scores["Regime"],
        orientation="h",
        marker_color=df_scores["color"],
        text=[f"{v:.3f}" for v in df_scores["Score"]],
        textposition="outside",
    ))
    fig.update_layout(
        height=260, margin=dict(t=20, b=20, l=20, r=20),
        xaxis_title="Score (1.0 max)",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("regime scores 없음")

if notes:
    st.markdown(f"**분류 노트:** {notes}")
if curve_signal:
    st.markdown(f"**곡선 노트:** {curve_signal.get('notes', '')}")

st.markdown("---")

# ============================================================
# Macro Readings 표
# ============================================================
st.subheader("Macro Readings 상세 (ECOS + FRED 자동 fetch)")

# 카테고리 분류
GROUPS = {
    "성장 (KR)":         ["kr_gdp_yoy", "kr_industrial_production_yoy",
                          "kr_exports_yoy", "kr_unemployment"],
    "인플레 (KR)":       ["kr_cpi_yoy", "kr_core_cpi_yoy"],
    "통화·금리 (KR)":    ["kr_base_rate", "kr_ktb_10y", "kr_ktb_3y",
                          "kr_curve_3y_10y", "kr_ktb_10y_change_20d",
                          "kr_ktb_3y_change_20d", "kr_curve_3y_10y_change_20d",
                          "kr_corp_aa_spread_bp"],
    "환율·원자재":       ["kr_usd_krw", "kr_brent_oil"],
    "글로벌":           ["us_fed_funds", "us_vix"],
}

# 한글 라벨 매핑
LABELS = {
    "kr_gdp_yoy":                   "한국 GDP YoY%",
    "kr_industrial_production_yoy": "한국 산업생산 YoY%",
    "kr_exports_yoy":               "한국 수출 YoY%",
    "kr_unemployment":              "한국 실업률 %",
    "kr_cpi_yoy":                   "한국 CPI YoY%",
    "kr_core_cpi_yoy":              "한국 근원 CPI YoY%",
    "kr_base_rate":                 "BOK 기준금리 %",
    "kr_ktb_10y":                   "KTB 10Y %",
    "kr_ktb_3y":                    "KTB 3Y %",
    "kr_curve_3y_10y":              "KTB 10Y-3Y 스프레드 %p",
    "kr_ktb_10y_change_20d":        "KTB 10Y 20영업일 변화 %p",
    "kr_ktb_3y_change_20d":         "KTB 3Y 20영업일 변화 %p",
    "kr_curve_3y_10y_change_20d":   "KTB 10Y-3Y 20영업일 변화 %p",
    "kr_corp_aa_spread_bp":         "회사채 AA- 스프레드 bp",
    "kr_usd_krw":                   "USD/KRW",
    "kr_brent_oil":                 "Brent 원유 $/배럴",
    "us_fed_funds":                 "미 연방기금금리 %",
    "us_vix":                       "VIX",
}

for group, keys in GROUPS.items():
    rows = []
    for k in keys:
        if k in readings:
            v = readings[k]
            prov = provenance.get(k, "static fallback")
            rows.append({
                "지표 (key)": LABELS.get(k, k),
                "값": v,
                "출처": prov,
                "내부 키": k,
            })
    if rows:
        st.markdown(f"**{group}**")
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True)

st.markdown("---")

# ============================================================
# 분석 메모 (analysis.md)
# ============================================================
analysis = load_md(OUTPUTS_DIR / "macro" / "analysis.md")
if analysis:
    with st.expander("MacroAgent 분석 메모 (analysis.md)", expanded=False):
        st.markdown(analysis)
