"""
기본 실행 결과 포트폴리오 상세.

데이터 소스:
  - outputs/cio/final_portfolio.json
  - outputs/cio/board_memo.md
  - outputs/macro/macro-view.json
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import (
    BOARD_MEMO_FILE,
    CATEGORY_COLORS,
    CIO_FILE,
    MACRO_FILE,
    category_of,
    category_totals,
    display_name,
    load_json,
    load_md,
    risk_asset_weight,
    render_sidebar,
)


st.set_page_config(page_title="현재 포트폴리오 — KR 연금", layout="wide")
render_sidebar()

st.title("현재 포트폴리오")
st.caption("기본 실행 결과: outputs/cio/final_portfolio.json")

cio = load_json(CIO_FILE)
macro = load_json(MACRO_FILE)
memo = load_md(BOARD_MEMO_FILE)

if cio is None:
    st.error(
        "`outputs/cio/final_portfolio.json`이 없습니다. 먼저 실행하세요:\n\n"
        "```powershell\n"
        "cd d:\\파이선\n"
        "python -m kr_pension_portfolio.run_pipeline\n"
        "```"
    )
    st.stop()

weights = cio.get("weights", {})
m = cio.get("metrics", {})
cat_totals = category_totals(weights)
risk_w = risk_asset_weight(weights)
curve = (macro or {}).get("curve_signal", {})

gen_ts = pd.Timestamp(Path(CIO_FILE).stat().st_mtime, unit="s").strftime("%Y-%m-%d %H:%M:%S")

st.info(
    f"**생성 시각**: {gen_ts}  |  "
    f"**선택 ensemble**: `{cio.get('chosen_ensemble', 'n/a')}`  |  "
    f"**거시 레짐**: {(macro or {}).get('regime', 'n/a')}"
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("위험자산 비중", f"{risk_w*100:.1f}%", f"한도 70% 대비 {(0.70-risk_w)*100:.1f}%p")
with c2:
    st.metric("기대수익률", f"{m.get('expected_return', 0)*100:.2f}%", f"변동성 {m.get('expected_vol', 0)*100:.2f}%")
with c3:
    st.metric("Backtest Sharpe", f"{m.get('backtest_sharpe', 0):.2f}", f"MDD {m.get('backtest_maxdd', 0)*100:.2f}%")
with c4:
    curve_label = curve.get("regime", "n/a") if curve else "n/a"
    st.metric("수익률곡선 상태", curve_label, f"TE {m.get('tracking_error', 0)*100:.2f}%")

left, right = st.columns([3, 2])

with left:
    st.subheader("카테고리 비중")
    fig = go.Figure(data=[go.Pie(
        labels=list(cat_totals.keys()),
        values=list(cat_totals.values()),
        hole=0.45,
        marker=dict(colors=[CATEGORY_COLORS[k] for k in cat_totals.keys()]),
        textinfo="label+percent",
        textposition="outside",
        sort=False,
    )])
    fig.update_layout(height=380, margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("ETF 비중")
    df = pd.DataFrame(
        [{"ETF": display_name(slug), "카테고리": category_of(slug), "비중": w} for slug, w in weights.items()]
    ).sort_values("비중", ascending=False)
    df["비중"] = df["비중"].map(lambda x: f"{x*100:.2f}%")
    st.dataframe(df, hide_index=True, use_container_width=True, height=380)

st.subheader("핵심 메트릭")
metrics_df = pd.DataFrame(
    [
        {"항목": "Expected Return", "값": f"{m.get('expected_return', 0)*100:.2f}%"},
        {"항목": "Expected Vol", "값": f"{m.get('expected_vol', 0)*100:.2f}%"},
        {"항목": "Tracking Error", "값": f"{m.get('tracking_error', 0)*100:.2f}%"},
        {"항목": "Effective N", "값": f"{m.get('effective_n', 0):.2f}"},
        {"항목": "Diversification", "값": f"{m.get('diversification', 0):.3f}"},
        {"항목": "IPS Compliance", "값": f"{m.get('ips_compliance', 0)*100:.0f}%"},
    ]
)
st.dataframe(metrics_df, hide_index=True, use_container_width=True)

if curve:
    st.subheader("수익률곡선 해석")
    st.markdown(
        f"- 상태: `{curve.get('regime', 'n/a')}`\n"
        f"- 형태: `{curve.get('shape', 'n/a')}`\n"
        f"- 20영업일 커브 변화: `{curve.get('curve_change_20d_bp', 0):+.1f}bp`\n"
        f"- 메모: {curve.get('notes', '')}"
    )

tilt = cio.get("fi_curve_tilt") or {}
if tilt.get("applied"):
    st.subheader("FI 수익률곡선 재배분 (FI 합계 보존)")
    st.caption(
        f"곡선 레짐 `{tilt['regime']}` · FI 카테고리 합계 "
        f"{tilt['fi_total']*100:.2f}% 유지 · 비-FI 자산군 비중 변동 없음"
    )
    pre = cio.get("weights_pre_tilt", {})
    post = cio.get("weights", {})
    rows = []
    for slug, dpp in sorted(tilt["shifts_pp"].items(), key=lambda kv: kv[1]):
        rows.append({
            "FI ETF": display_name(slug),
            "프로필": (
                "long_duration" if slug in {"kr-treasuries-10y", "us-treasuries-10y", "us-treasuries-30y"}
                else "cash_like" if slug == "kr-short-bonds"
                else "credit"
            ),
            "Pre-tilt": f"{pre.get(slug, 0)*100:.2f}%",
            "Post-tilt": f"{post.get(slug, 0)*100:.2f}%",
            "Δ (pp)": f"{dpp:+.2f}",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

if memo:
    st.subheader("Board Memo")
    st.markdown(memo)
else:
    st.info("`outputs/cio/board_memo.md`가 아직 없습니다.")
