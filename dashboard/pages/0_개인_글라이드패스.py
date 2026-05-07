"""
개인 맞춤형 글라이드패스 (PoC)

흐름:
  1) 입력 — 나이/직업/은퇴시점/현금흐름 시계열/TDF SAA + 적격 체크
  2) 맞춤형 현금흐름 접근법 → 35년치 stock/bond/cash 글라이드패스
  3) 현 시점 타겟에 TDF 안전밸브 매핑 → 직접 운용분 + TDF 위임분 + 룩스루 합계
  4) IPS 한도와 충돌 시 맞춤형 결과를 우선 적용 (정보성 표시)
  5) [신규] '맞춤형 IPS 생성 + 파이프라인 실행' → 18 ETF 세부 비중 + TDF 합성 표시
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Project paths
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))   # d:/파이선

from utils import CATEGORY_COLORS, render_sidebar
from kr_pension_portfolio.skills.personalized_glidepath import (
    GlidePathInputs, TDFInputs,
    PERSONALIZED_OUT_DIR,
    build_personalized_ips,
    compose_with_tdf,
    compute_personalized_allocation,
    load_personalized_result,
    run_personalized_pipeline,
    run_yuanta_glidepath,
    save_personalized_ips,
)


# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(page_title="개인 글라이드패스 — KR 연금", layout="wide")
render_sidebar()

st.title("개인 맞춤형 글라이드패스 (PoC)")
st.caption("맞춤형 현금흐름 접근법(현금흐름·인적자본·생애주기 통합) + TDF 안전밸브로 DC/IRP 70% 한도 우회")


# ============================================================
# 1. 입력
# ============================================================
st.subheader("1. 입력")

c1, c2, c3 = st.columns(3)
with c1:
    age = st.number_input("현재 나이", 25, 75, 35, 1)
    retirement_age = st.number_input("은퇴 시점", value=60, min_value=age + 1, max_value=80, step=1)
    occupation = st.selectbox("직업군 (HC 베타)", [
        "공무원", "교사", "의사", "직장인", "전문직", "IT", "자영업", "창업가"
    ], index=3)

with c2:
    st.markdown("**최근 5년 순현금흐름** (만원, 콤마 구분)")
    cf_default = "3000, 3200, 3400, 3600, 3800"
    cf_text = st.text_area("현금흐름 시계열", cf_default, height=80,
                            help="저축액 + 투자수익 - 지출. 양수=축적, 음수=인출. 최소 3개.")
    try:
        cashflow_series = [float(x.strip()) for x in cf_text.split(",") if x.strip()]
        if len(cashflow_series) < 3:
            st.warning("최소 3개 데이터 필요")
            st.stop()
    except ValueError:
        st.error("숫자 파싱 실패")
        st.stop()

with c3:
    st.markdown("**TDF (적격) 정보**")
    tdf_name = st.text_input("TDF 이름", "미래에셋 TDF 2050")
    tdf_stock = st.slider("TDF 내부 주식 비중", 0.0, 1.0, 0.80, 0.05)
    tdf_bond = st.slider("TDF 내부 채권 비중", 0.0, 1.0, 0.18, 0.02)
    tdf_real = st.slider("TDF 내부 대안 비중", 0.0, 0.30, 0.02, 0.01)
    tdf_cash = max(0.0, 1.0 - tdf_stock - tdf_bond - tdf_real)
    st.caption(f"내부 현금 잔여: {tdf_cash*100:.1f}% (자동 계산)")
    tdf_eligible = st.checkbox("**적격TDF** — 70% 위험자산 한도 예외 적용", value=True,
                               help="근로자퇴직급여 보장법 시행령에 따라 적격TDF는 cap 예외. "
                                    "운용사 자료에서 적격 여부 확인 필수.")
    tdf_max = st.slider("TDF 비중 상한 (안전장치)", 0.0, 0.95, 0.50, 0.05,
                        help="마스터 공식이 극단으로 가도 TDF가 너무 커지지 않도록 한도 설정.")


# ============================================================
# 2. 맞춤형 현금흐름 접근법 글라이드패스 실행
# ============================================================
st.markdown("---")
st.subheader("2. 글라이드패스 (맞춤형 현금흐름 접근법)")

g_in = GlidePathInputs(
    age=age, retirement_age=retirement_age, occupation=occupation,
    cashflow_series=cashflow_series, horizon_years=max(35, retirement_age - age + 25),
)

try:
    df = run_yuanta_glidepath(g_in)
except Exception as e:
    st.error(f"맞춤형 현금흐름 엔진 실행 실패: {e}")
    st.stop()

cM, cP = st.columns([2, 1])
with cM:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["age"], y=df["final_allocation"]*100,
                             mode="lines", name="주식", line=dict(color=CATEGORY_COLORS["Equity"], width=3)))
    fig.add_trace(go.Scatter(x=df["age"], y=df["bonds_allocation"]*100,
                             mode="lines", name="채권", line=dict(color=CATEGORY_COLORS["FixedIncome"], width=3)))
    fig.add_trace(go.Scatter(x=df["age"], y=df["cash_allocation"]*100,
                             mode="lines", name="현금", line=dict(color=CATEGORY_COLORS["Cash"], width=3)))
    fig.add_hline(y=70, line=dict(color="red", dash="dash"),
                  annotation_text="DC/IRP 직접운용 70% 한도", annotation_position="top right")
    fig.add_vline(x=retirement_age, line=dict(color="gray", dash="dot"),
                  annotation_text=f"은퇴 {retirement_age}세")
    fig.update_layout(
        height=380, margin=dict(t=20, b=10, l=10, r=10),
        xaxis=dict(title="연령"), yaxis=dict(title="비중 (%)", range=[0, 100]),
        legend=dict(orientation="h", y=1.05, x=0),
    )
    st.plotly_chart(fig, use_container_width=True)
with cP:
    st.markdown("**진단**")
    st.markdown(
        f"- 현금흐름 패턴: **{df.attrs.get('pattern', 'n/a')}**\n"
        f"- 안정성 점수: `{df.attrs.get('stability', 0):.2f}`\n"
        f"- 직업 HC β: `{df.attrs.get('hc_beta', 0):.2f}`\n"
        f"- HC 조정값: `{df.attrs.get('hc_adjustment', 0):+.3f}`\n"
        f"- 분석 신뢰도: `{df.attrs.get('confidence', 0):.0%}`"
    )


# ============================================================
# 3. 현재 연령 타겟 → TDF 안전밸브 매핑
# ============================================================
st.markdown("---")
st.subheader(f"3. {age}세 시점 — 자산 매핑 (직접 ETF + TDF + 룩스루)")

row = df[df["age"] == age].iloc[0]
target_stock = float(row["final_allocation"])
target_bond = float(row["bonds_allocation"])
target_cash = float(row["cash_allocation"])

tdf_in = TDFInputs(
    name=tdf_name, stock=tdf_stock, bond=tdf_bond,
    real_asset=tdf_real, cash=tdf_cash,
    eligible=tdf_eligible, max_holding=tdf_max,
)
alloc = compute_personalized_allocation(
    target_stock, target_bond, target_cash, tdf_in,
    ips_equity_max=0.55, ips_real_max=0.15, ips_fi_min=0.20, risky_cap=0.70,
)
lt = alloc.lookthrough()

# KPIs
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("맞춤형 주식 타겟", f"{target_stock*100:.1f}%")
with k2:
    st.metric("TDF 비중 (T)", f"{alloc.tdf_holding*100:.1f}%",
              "feasible" if alloc.feasible else "infeasible",
              delta_color="normal" if alloc.feasible else "inverse")
with k3:
    delta_pp = (lt["Equity"] - target_stock) * 100
    st.metric("룩스루 주식 노출", f"{lt['Equity']*100:.2f}%",
              f"{delta_pp:+.2f}pp vs 타겟",
              delta_color="off")
with k4:
    risky = (alloc.direct_equity + alloc.direct_real) * 100
    st.metric("직접 운용 위험자산", f"{risky:.1f}%",
              f"DC/IRP cap 70% 대비 {70-risky:.1f}%p 여유",
              delta_color="off")

# 3-column 표
ccD, ccT, ccLT = st.columns(3)

with ccD:
    st.markdown("##### 직접 운용분 (18 ETF)")
    ddf = pd.DataFrame([
        {"카테고리": "Equity",      "비중 (%)": alloc.direct_equity * 100},
        {"카테고리": "FixedIncome", "비중 (%)": alloc.direct_fi * 100},
        {"카테고리": "RealAssets",  "비중 (%)": alloc.direct_real * 100},
        {"카테고리": "Cash",        "비중 (%)": alloc.direct_cash * 100},
    ])
    direct_total = ddf["비중 (%)"].sum()
    st.dataframe(
        ddf.assign(**{"비중 (%)": ddf["비중 (%)"].map(lambda x: f"{x:.2f}")}),
        hide_index=True, use_container_width=True
    )
    st.caption(f"직접 합계: **{direct_total:.2f}%** (= 1 − T)")

with ccT:
    st.markdown(f"##### TDF 위임분 — {tdf_name}")
    tdf_inner = alloc.tdf_internal_saa
    tdf_T = alloc.tdf_holding
    tdf_df = pd.DataFrame([
        {"카테고리": "Equity",      "내부 SAA (%)": tdf_inner["stock"] * 100,      "외부 환산 (%)": tdf_T * tdf_inner["stock"] * 100},
        {"카테고리": "FixedIncome", "내부 SAA (%)": tdf_inner["bond"] * 100,       "외부 환산 (%)": tdf_T * tdf_inner["bond"] * 100},
        {"카테고리": "RealAssets",  "내부 SAA (%)": tdf_inner["real_asset"] * 100, "외부 환산 (%)": tdf_T * tdf_inner["real_asset"] * 100},
        {"카테고리": "Cash",        "내부 SAA (%)": tdf_inner["cash"] * 100,       "외부 환산 (%)": tdf_T * tdf_inner["cash"] * 100},
    ])
    fmt = tdf_df.copy()
    fmt["내부 SAA (%)"] = fmt["내부 SAA (%)"].map(lambda x: f"{x:.1f}")
    fmt["외부 환산 (%)"] = fmt["외부 환산 (%)"].map(lambda x: f"{x:.2f}")
    st.dataframe(fmt, hide_index=True, use_container_width=True)
    st.caption(f"TDF 보유 = **{tdf_T*100:.2f}%** · 적격 = `{tdf_eligible}`")

with ccLT:
    st.markdown("##### 룩스루 합계")
    lt_df = pd.DataFrame([
        {"카테고리": k, "비중 (%)": v * 100, "맞춤형 타겟 (%)": (
            target_stock if k == "Equity"
            else target_bond if k == "FixedIncome"
            else 0.0 if k == "RealAssets"
            else target_cash
        ) * 100}
        for k, v in lt.items()
    ])
    lt_df["Δ (pp)"] = lt_df["비중 (%)"] - lt_df["맞춤형 타겟 (%)"]
    fmt = lt_df.copy()
    fmt["비중 (%)"] = fmt["비중 (%)"].map(lambda x: f"{x:.2f}")
    fmt["맞춤형 타겟 (%)"] = fmt["맞춤형 타겟 (%)"].map(lambda x: f"{x:.1f}")
    fmt["Δ (pp)"] = fmt["Δ (pp)"].map(lambda x: f"{x:+.2f}")
    st.dataframe(fmt, hide_index=True, use_container_width=True)
    st.caption(f"룩스루 합계: **{sum(lt.values())*100:.2f}%**")

# 도넛 비교
st.markdown("##### 카테고리 비중 시각화 (룩스루 vs 맞춤형 타겟)")
cD1, cD2 = st.columns(2)
labels = list(lt.keys())
with cD1:
    fig_lt = go.Figure(data=[go.Pie(
        labels=labels, values=[lt[k] for k in labels], hole=0.45,
        marker=dict(colors=[CATEGORY_COLORS[k] for k in labels]),
        textinfo="label+percent", sort=False,
    )])
    fig_lt.update_layout(title_text="룩스루 합계 (직접 + TDF)",
                         height=320, margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
    st.plotly_chart(fig_lt, use_container_width=True)
with cD2:
    yuanta_view = {"Equity": target_stock, "FixedIncome": target_bond,
                   "RealAssets": 0.0, "Cash": target_cash}
    fig_yu = go.Figure(data=[go.Pie(
        labels=list(yuanta_view.keys()), values=list(yuanta_view.values()), hole=0.45,
        marker=dict(colors=[CATEGORY_COLORS[k] for k in yuanta_view.keys()]),
        textinfo="label+percent", sort=False,
    )])
    fig_yu.update_layout(title_text="맞춤형 현금흐름 접근법 타겟",
                         height=320, margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
    st.plotly_chart(fig_yu, use_container_width=True)


# ============================================================
# 4. 진단 / 경고
# ============================================================
st.markdown("---")
st.subheader("4. 진단")

if alloc.notes:
    for n in alloc.notes:
        st.warning(n)
else:
    st.success("매핑 결과 IPS 제약 모두 충족.")

with st.expander("산출 공식 보기"):
    st.markdown(
        f"""
**TDF 안전밸브 공식** (target_stock > IPS Equity max인 경우):

```
T = (target_stock - E_max) / stock_TDF
direct_equity_abs = E_max
look_through_stock = E_max + T × stock_TDF = target_stock
```

**현재 입력 적용**:

- target_stock = {target_stock*100:.1f}%
- E_max (IPS Equity max) = 55%
- stock_TDF = {tdf_stock*100:.0f}%
- T = ({target_stock*100:.1f} − 55) / {tdf_stock*100:.0f} = **{alloc.tdf_holding*100:.2f}%**
- 룩스루 stock = 55 + {alloc.tdf_holding*100:.2f} × {tdf_stock*100:.0f}% = **{lt['Equity']*100:.2f}%**

**Feasibility 조건**:
- 적격TDF여야 70% cap 우회 가능
- T ≤ min(tdf_max, 1 − E_max) — 직접 portion이 IPS Equity max 수용 가능해야
- stock_TDF > 0 (그렇지 않으면 TDF가 stock 추가 불가)
        """
    )

st.caption("4-카테고리 비중을 IPS yaml로 저장하고 `run_pipeline`을 호출해 18 ETF 세부 비중을 결정.")


# ============================================================
# 5. 18 ETF 세부 비중 (맞춤형 IPS + 파이프라인)
# ============================================================
st.markdown("---")
st.subheader("5. 18 ETF 세부 비중 (맞춤형 IPS 기반)")

# Persistent results in session state to avoid reload thrash
if "p_cio" not in st.session_state:
    st.session_state["p_cio"] = None
    st.session_state["p_tdf_holding"] = None
    st.session_state["p_tdf_name"] = None
    st.session_state["p_tdf_internal"] = None

st.caption(
    "버튼을 누르면 (1) 위 4-카테고리 비중을 `configs/ips_personalized.yaml`로 저장 → "
    "(2) `run_pipeline` 실행 (~30초) → (3) `outputs_personalized/cio/final_portfolio.json` 로드. "
    "엔진은 직접 운용분(1−T)에 대한 18 ETF 비중을 산출하고, 화면에서 TDF를 별도 라인으로 합성합니다."
)

cb1, cb2 = st.columns([1, 3])
with cb1:
    run_btn = st.button("맞춤형 IPS 생성 + 파이프라인 실행", type="primary", use_container_width=True)
with cb2:
    if st.button("이전 결과만 로드 (실행 없이)", use_container_width=True):
        cio_p, _ = load_personalized_result(PERSONALIZED_OUT_DIR)
        if cio_p is None:
            st.warning(f"`outputs_personalized/cio/final_portfolio.json` 없음 — 먼저 실행하세요.")
        else:
            st.session_state["p_cio"] = cio_p
            st.session_state["p_tdf_holding"] = alloc.tdf_holding
            st.session_state["p_tdf_name"] = tdf_name
            st.session_state["p_tdf_internal"] = alloc.tdf_internal_saa

if run_btn:
    with st.spinner("맞춤형 IPS 생성 중..."):
        pers_ips = build_personalized_ips(alloc)
        ips_path = save_personalized_ips(pers_ips)
    st.success(f"IPS 저장: `{ips_path.name}`")
    with st.spinner("파이프라인 실행 중 (~30초)..."):
        try:
            run_personalized_pipeline()
            cio_p, _ = load_personalized_result(PERSONALIZED_OUT_DIR)
            st.session_state["p_cio"] = cio_p
            st.session_state["p_tdf_holding"] = alloc.tdf_holding
            st.session_state["p_tdf_name"] = tdf_name
            st.session_state["p_tdf_internal"] = alloc.tdf_internal_saa
            st.success("파이프라인 완료. 아래에 결과 표시.")
        except Exception as e:
            st.error(f"파이프라인 실패: {e}")

cio_p = st.session_state["p_cio"]
if cio_p is None:
    st.info("아직 실행 결과가 없습니다.")
else:
    direct_weights = cio_p.get("weights", {})
    T_disp = st.session_state["p_tdf_holding"] or 0.0
    tdf_name_disp = st.session_state["p_tdf_name"] or "TDF"
    tdf_internal_disp = st.session_state["p_tdf_internal"] or {}
    composed = compose_with_tdf(direct_weights, T_disp, tdf_name=tdf_name_disp)

    # IPS 카테고리 매핑 (직접 ETF용)
    cat_map_18 = {
        "kr-large-cap":"Equity","kr-kosdaq":"Equity","kr-dividend":"Equity",
        "us-large-cap":"Equity","us-tech":"Equity","us-dividend":"Equity",
        "intl-developed":"Equity","emerging-markets":"Equity",
        "kr-treasuries-10y":"FixedIncome","kr-short-bonds":"FixedIncome","kr-credit":"FixedIncome",
        "us-treasuries-10y":"FixedIncome","us-treasuries-30y":"FixedIncome","us-ig-credit":"FixedIncome",
        "gold":"RealAssets","commodities":"RealAssets",
        "kofr-cash":"Cash","money-market":"Cash",
    }
    composed["category"] = composed.apply(
        lambda r: "TDF" if r["kind"] == "tdf" else cat_map_18.get(r["slug"], "?"), axis=1
    )

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("직접 ETF 합계", f"{(1.0-T_disp)*100:.2f}%", "= 18 ETF × (1−T)")
    with m2:
        st.metric("TDF 비중", f"{T_disp*100:.2f}%", tdf_name_disp)
    with m3:
        st.metric("총 합계", f"{composed['weight'].sum()*100:.2f}%", "(should = 100)")

    # ETF 표
    sl, sr = st.columns([3, 2])
    with sl:
        view = composed.sort_values(["kind", "weight"], ascending=[False, False]).copy()
        view["비중 (%)"] = view["weight"].map(lambda x: f"{x*100:.2f}")
        st.dataframe(
            view[["slug", "category", "비중 (%)", "kind"]].rename(
                columns={"slug": "ETF/TDF", "category": "카테고리", "kind": "구분"}
            ),
            hide_index=True, use_container_width=True, height=460,
        )
    with sr:
        # 카테고리 합계 (룩스루: TDF 내부 SAA 분해)
        cat_sums = {"Equity": 0.0, "FixedIncome": 0.0, "RealAssets": 0.0, "Cash": 0.0}
        for _, r in composed.iterrows():
            if r["kind"] == "direct":
                cat_sums[r["category"]] = cat_sums.get(r["category"], 0.0) + r["weight"]
            else:
                cat_sums["Equity"]      += r["weight"] * tdf_internal_disp.get("stock", 0.0)
                cat_sums["FixedIncome"] += r["weight"] * tdf_internal_disp.get("bond", 0.0)
                cat_sums["RealAssets"]  += r["weight"] * tdf_internal_disp.get("real_asset", 0.0)
                cat_sums["Cash"]        += r["weight"] * tdf_internal_disp.get("cash", 0.0)

        fig_p = go.Figure(data=[go.Pie(
            labels=list(cat_sums.keys()),
            values=[v*100 for v in cat_sums.values()],
            hole=0.45,
            marker=dict(colors=[CATEGORY_COLORS[k] for k in cat_sums.keys()]),
            textinfo="label+percent", sort=False,
        )])
        fig_p.update_layout(title_text="룩스루 카테고리 합계 (18 ETF + TDF 분해)",
                            height=380, margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
        st.plotly_chart(fig_p, use_container_width=True)

        # 룩스루 vs 맞춤형 타겟 비교
        target_view = {"Equity": target_stock, "FixedIncome": target_bond,
                       "RealAssets": 0.0, "Cash": target_cash}
        comp_df = pd.DataFrame([
            {"카테고리": k, "룩스루 (%)": cat_sums[k]*100, "맞춤형 타겟 (%)": target_view[k]*100,
             "Δ (pp)": (cat_sums[k] - target_view[k])*100}
            for k in cat_sums
        ])
        fmt = comp_df.copy()
        for c in ["룩스루 (%)", "맞춤형 타겟 (%)"]:
            fmt[c] = fmt[c].map(lambda x: f"{x:.2f}")
        fmt["Δ (pp)"] = fmt["Δ (pp)"].map(lambda x: f"{x:+.2f}")
        st.dataframe(fmt, hide_index=True, use_container_width=True)

    # 메트릭
    m = cio_p.get("metrics", {})
    st.markdown("##### 엔진 메트릭 (직접 운용분)")
    mm = pd.DataFrame([
        {"항목": "Expected Return", "값": f"{m.get('expected_return', 0)*100:.2f}%"},
        {"항목": "Expected Vol",    "값": f"{m.get('expected_vol', 0)*100:.2f}%"},
        {"항목": "Backtest Sharpe", "값": f"{m.get('backtest_sharpe', 0):.2f}"},
        {"항목": "Backtest MDD",    "값": f"{m.get('backtest_maxdd', 0)*100:.2f}%"},
        {"항목": "Tracking Error",  "값": f"{m.get('tracking_error', 0)*100:.2f}%"},
        {"항목": "Diversification", "값": f"{m.get('diversification', 0):.3f}"},
        {"항목": "선택 ensemble",    "값": cio_p.get("chosen_ensemble", "n/a")},
    ])
    st.dataframe(mm, hide_index=True, use_container_width=True)

    # FI 곡선 tilt 정보 (직접 운용분에 적용된 것)
    tilt = cio_p.get("fi_curve_tilt") or {}
    if tilt.get("applied"):
        st.caption(
            f"직접 운용분 FI에 곡선 tilt 적용됨 — 레짐 `{tilt['regime']}`, "
            f"FI 합계 {tilt['fi_total']*100:.2f}% (직접 운용분 내 비율) 보존."
        )
