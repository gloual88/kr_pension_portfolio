"""
자산군별 분석 — 18 KR-listed ETF.

각 자산군의 CMA, historical stats, signals, 분석 메모를 제공합니다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import (
    load_json, load_md, ASSETS_DIR, CIO_FILE,
    asset_class_meta, category_of, display_name, CATEGORY_COLORS,
    render_sidebar,
)


st.set_page_config(page_title="자산군 분석 — KR 연금", layout="wide")
render_sidebar()

st.title("자산군 분석")
st.caption("18 KR-listed ETF — DC/IRP 가능 (레버리지/인버스 제외)")

meta = asset_class_meta()
cio = load_json(CIO_FILE) or {}
weights = cio.get("weights", {})

# ============================================================
# 18 ETF 종합 표
# ============================================================
st.subheader("18 ETF 종합")

rows = []
for slug, ac in meta.items():
    cma = load_json(ASSETS_DIR / slug / "cma.json")
    er = cma.get("expected_return") if cma else None
    vol = cma.get("expected_vol") if cma else None
    rows.append({
        "Slug": slug,
        "ETF 코드": ac.get("etf", ""),
        "ETF 이름": ac.get("name", ""),
        "카테고리": ac.get("category", ""),
        "현재 비중": f"{weights.get(slug, 0)*100:.2f}%",
        "E[r] (연)": f"{er*100:.2f}%" if er is not None else "-",
        "σ (연)": f"{vol*100:.2f}%" if vol is not None else "-",
        "환헤지": "O" if ac.get("hedged", False) else "-",
    })

df = pd.DataFrame(rows)
df = df.sort_values(["카테고리", "Slug"]).reset_index(drop=True)
st.dataframe(df, hide_index=True, use_container_width=True, height=420)

st.markdown("---")

# ============================================================
# 자산군 선택 → 상세 패널
# ============================================================
st.subheader("자산군 상세")

slugs = list(meta.keys())
default_slug = "kr-large-cap" if "kr-large-cap" in slugs else slugs[0]
selected = st.selectbox(
    "자산군 선택",
    options=slugs,
    index=slugs.index(default_slug),
    format_func=lambda s: f"{s} — {display_name(s)} ({category_of(s)})",
)

ac = meta.get(selected, {})
ac_dir = ASSETS_DIR / selected

# 상단 카드
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("ETF", ac.get("etf", "-"))
with c2:
    st.metric("카테고리", ac.get("category", "-"))
with c3:
    st.metric("현재 비중", f"{weights.get(selected, 0)*100:.2f}%")
with c4:
    cma = load_json(ac_dir / "cma.json") or {}
    er = cma.get("expected_return")
    vol = cma.get("expected_vol")
    if er is not None and vol is not None:
        sharpe_implied = (er - 0.030) / vol if vol > 0 else 0
        st.metric("Implied Sharpe", f"{sharpe_implied:.2f}",
                  f"E[r] {er*100:.2f}% / σ {vol*100:.2f}%")
    else:
        st.metric("Implied Sharpe", "-")

# CMA + signals + historical
tabs = st.tabs(["CMA (방법별)", "Historical Stats", "Signals", "Analysis Memo"])

with tabs[0]:
    cma_methods = load_json(ac_dir / "cma_methods.json")
    if cma_methods:
        method_rows = []
        for name, vals in cma_methods.items():
            if isinstance(vals, dict):
                method_rows.append({
                    "방법": name,
                    "E[r]": f"{vals.get('expected_return', 0)*100:.2f}%"
                            if vals.get('expected_return') is not None else "-",
                    "σ": f"{vals.get('expected_vol', 0)*100:.2f}%"
                         if vals.get('expected_vol') is not None else "-",
                    "비고": vals.get("note", "") or vals.get("rationale", ""),
                })
        if method_rows:
            st.dataframe(pd.DataFrame(method_rows), hide_index=True,
                         use_container_width=True)
        else:
            st.json(cma_methods)
    else:
        st.info("`cma_methods.json` 없음")

with tabs[1]:
    hist = load_json(ac_dir / "historical_stats.json")
    if hist:
        # 표 형태로 평탄화
        flat = []
        for k, v in hist.items():
            if isinstance(v, (int, float)):
                if "return" in k.lower() or "vol" in k.lower() or "drawdown" in k.lower():
                    flat.append({"지표": k, "값": f"{v*100:.2f}%"})
                else:
                    flat.append({"지표": k, "값": f"{v:.4f}" if isinstance(v, float) else v})
            else:
                flat.append({"지표": k, "값": str(v)})
        if flat:
            st.dataframe(pd.DataFrame(flat), hide_index=True, use_container_width=True)
        else:
            st.json(hist)
    else:
        st.info("`historical_stats.json` 없음")

with tabs[2]:
    sig = load_json(ac_dir / "signals.json")
    if sig:
        sig_rows = []
        for k, v in sig.items():
            if isinstance(v, (int, float)):
                sig_rows.append({"시그널": k, "값": f"{v:.4f}"})
            else:
                sig_rows.append({"시그널": k, "값": str(v)[:80]})
        if sig_rows:
            st.dataframe(pd.DataFrame(sig_rows), hide_index=True,
                         use_container_width=True)
        else:
            st.json(sig)
    else:
        st.info("`signals.json` 없음")

with tabs[3]:
    md = load_md(ac_dir / "analysis.md")
    if md:
        st.markdown(md)
    else:
        st.info("`analysis.md` 없음")
