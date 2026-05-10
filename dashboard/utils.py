"""
Common data loaders + helpers for the KR pension dashboard.

All paths are resolved relative to kr_pension_portfolio/outputs/, which is
populated by:
  - run_pipeline.py            → cio/, macro/, asset_classes/, ...
  - backtest_walk_forward_kr.py → backtest_kr/, backtest_kr_llm/

Streamlit caching is applied where reads are filesystem-bound.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

# ----- Paths -----
DASH_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DASH_DIR.parent
OUTPUTS_DIR = PROJECT_DIR / "outputs"
BT_BASELINE = OUTPUTS_DIR / "backtest_kr"
BT_LLM = OUTPUTS_DIR / "backtest_kr_llm"
BT_LLM_PHASE2 = OUTPUTS_DIR / "backtest_kr_llm_phase2"
BT_LOCK70_BASELINE = OUTPUTS_DIR / "backtest_kr_lock70"
BT_LOCK70_PHASE2   = OUTPUTS_DIR / "backtest_kr_lock70_llm_phase2"
CIO_FILE = OUTPUTS_DIR / "cio" / "final_portfolio.json"
BOARD_MEMO_FILE = OUTPUTS_DIR / "cio" / "board_memo.md"
MACRO_FILE = OUTPUTS_DIR / "macro" / "macro-view.json"
ASSETS_DIR = OUTPUTS_DIR / "asset_classes"
IPS_FILE = PROJECT_DIR / "configs" / "ips.yaml"

# v2 hybrid (KR/US/Global multi-regime) — bundled into v1 outputs/ for Cloud deploy
# Source data lives in kr_pension_hybrid/outputs/v2_*_wf/, copied via:
#   cp metrics.json nav_*.csv weights_quarterly.csv regime_history.csv → outputs/v2_*/
# Re-copy after re-running v2 walk-forward.
HYBRID_OUTPUTS_DIR = PROJECT_DIR.parent / "kr_pension_hybrid" / "outputs"   # source of truth
BT_V2_BASELINE       = OUTPUTS_DIR / "v2_baseline"          # bundled
BT_V2_SCORE          = OUTPUTS_DIR / "v2_score"             # bundled
BT_V2_PHASE2         = OUTPUTS_DIR / "v2_phase2"            # bundled
BT_V2_SCORE_GLOBALBM   = OUTPUTS_DIR / "v2_score_globalbm"    # v0.4.1 global BM
BT_V2_SCORE_SENS       = OUTPUTS_DIR / "v2_score_sens"        # v0.4.2 macro_sensitivity
BT_V2_SCORE_AGGRESSIVE = OUTPUTS_DIR / "v2_score_aggressive"      # v0.5 aggressive IPS
BT_V2_SCORE_AGG_PCR    = OUTPUTS_DIR / "v2_score_aggressive_pcr"  # v0.5.1 + PC re-weight

# Variant → directory mapping (used by all loaders below)
VARIANT_DIRS = {
    "lock70_baseline":   BT_LOCK70_BASELINE,
    "lock70_phase2":     BT_LOCK70_PHASE2,
    "baseline":   BT_BASELINE,
    "llm":        BT_LLM,
    "llm_phase2": BT_LLM_PHASE2,
    "v2_baseline": BT_V2_BASELINE,
    "v2_score":    BT_V2_SCORE,
    "v2_phase2":   BT_V2_PHASE2,
    "v2_score_globalbm": BT_V2_SCORE_GLOBALBM,
    "v2_score_sens":     BT_V2_SCORE_SENS,
    "v2_score_aggressive": BT_V2_SCORE_AGGRESSIVE,
    "v2_score_aggressive_pcr": BT_V2_SCORE_AGG_PCR,
}
VARIANT_LABELS = {
    "lock70_baseline":   "v1 lock70 Baseline (위험자산 70% 고정, 2026-05-10) ★",
    "lock70_phase2":     "v1 lock70 Phase 2 (Claude CIO + CMA, 위험자산 70% 고정)",
    "baseline":   "v1 Baseline (구 IPS, stub, single regime, KR 60/40 BM)",
    "llm":        "v1 Phase 1 (구 IPS, Claude CIO)",
    "llm_phase2": "v1 Phase 2 (구 IPS, Claude CIO + CMA)",
    "v2_baseline": "v2 Baseline (KR/US/Global, label, KR 60/40 BM)",
    "v2_score":    "v2 Score Injection (KR/US/Global, score)",
    "v2_phase2":   "v2 Phase 2 LLM (KR/US/Global + Claude)",
    "v2_score_globalbm": "v2 Score + Global BM (KR30+US30+Bond40)",
    "v2_score_sens":     "v2 Score + macro_sensitivity (자산별 sens 곱)",
    "v2_score_aggressive": "v2 Score + Aggressive IPS (risky 40% floor)",
    "v2_score_aggressive_pcr": "v2 Score + Aggr IPS + PC re-weight (return-seek tilt) ★",
}

# ----- Categories -----
CATEGORY_COLORS = {
    "Equity": "#1f4e79",
    "FixedIncome": "#7e9bb8",
    "RealAssets": "#c89b3c",
    "Cash": "#5b8a72",
}


# ----- Loaders -----
@st.cache_data(show_spinner=False)
def load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_md(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


@st.cache_data(show_spinner=False)
def load_ips() -> Optional[dict]:
    if not IPS_FILE.exists():
        return None
    import yaml
    with open(IPS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@st.cache_data(show_spinner=False)
def load_nav(variant: str = "baseline") -> Optional[pd.DataFrame]:
    """Load NAV CSVs for agentic + benchmark and merge by date."""
    bt_dir = VARIANT_DIRS.get(variant, BT_BASELINE)
    a = bt_dir / "nav_agentic.csv"
    b = bt_dir / "nav_benchmark.csv"
    if not a.exists() or not b.exists():
        return None
    da = pd.read_csv(a, parse_dates=["date"]).set_index("date")
    db = pd.read_csv(b, parse_dates=["date"]).set_index("date")
    df = da.join(db, how="outer")
    df.columns = ["agentic", "benchmark"]
    return df


@st.cache_data(show_spinner=False)
def load_weights(variant: str = "baseline") -> Optional[pd.DataFrame]:
    bt_dir = VARIANT_DIRS.get(variant, BT_BASELINE)
    p = bt_dir / "weights_quarterly.csv"
    if not p.exists():
        return None
    return pd.read_csv(p, parse_dates=["date"]).set_index("date")


@st.cache_data(show_spinner=False)
def load_regime_history(variant: str = "baseline") -> Optional[pd.DataFrame]:
    bt_dir = VARIANT_DIRS.get(variant, BT_BASELINE)
    p = bt_dir / "regime_history.csv"
    if not p.exists():
        return None
    return pd.read_csv(p, parse_dates=["as_of"])


@st.cache_data(show_spinner=False)
def load_metrics(variant: str = "baseline") -> Optional[dict]:
    bt_dir = VARIANT_DIRS.get(variant, BT_BASELINE)
    return load_json(bt_dir / "metrics.json")


@st.cache_data(show_spinner=False)
def load_variant_current_cio(variant: str) -> Optional[dict]:
    """Load latest single-shot CIO payload for a v2 variant (cio/final_portfolio.json)."""
    bt_dir = VARIANT_DIRS.get(variant)
    if bt_dir is None:
        return None
    return load_json(bt_dir / "cio" / "final_portfolio.json")


@st.cache_data(show_spinner=False)
def load_variant_current_macro(variant: str) -> Optional[dict]:
    """Load latest single-shot macro payload for a v2 variant (macro/macro-view.json)."""
    bt_dir = VARIANT_DIRS.get(variant)
    if bt_dir is None:
        return None
    return load_json(bt_dir / "macro" / "macro-view.json")


@st.cache_data(show_spinner=False)
def load_variant_board_memo(variant: str) -> Optional[str]:
    bt_dir = VARIANT_DIRS.get(variant)
    if bt_dir is None:
        return None
    return load_md(bt_dir / "cio" / "board_memo.md")


def available_variants() -> list:
    """Return list of variants whose metrics.json exists."""
    return [v for v in VARIANT_DIRS if (VARIANT_DIRS[v] / "metrics.json").exists()]


# ----- IPS / asset class mapping -----
@st.cache_data(show_spinner=False)
def asset_class_meta() -> Dict[str, dict]:
    """Build {slug: {category, name, etf, ...}} from IPS yaml."""
    ips = load_ips()
    if not ips:
        return {}
    out = {}
    for ac in ips.get("investment_universe", {}).get("asset_classes", []):
        out[ac["slug"]] = ac
    return out


def category_of(slug: str) -> str:
    meta = asset_class_meta().get(slug, {})
    return meta.get("category", "Unknown")


def display_name(slug: str) -> str:
    """Human-friendly label combining ETF code + Korean name when available."""
    meta = asset_class_meta().get(slug, {})
    etf = meta.get("etf", "")
    name = meta.get("name", slug)
    if etf:
        return f"{etf} {name}"
    return slug


def category_totals(weights: Dict[str, float]) -> Dict[str, float]:
    """Sum weights by IPS category."""
    totals = {"Equity": 0.0, "FixedIncome": 0.0, "RealAssets": 0.0, "Cash": 0.0}
    for slug, w in weights.items():
        cat = category_of(slug)
        if cat in totals:
            totals[cat] += float(w)
    return totals


def risk_asset_weight(weights: Dict[str, float]) -> float:
    """Equity + RealAssets — must be ≤ 70% under DC/IRP regulation."""
    cats = category_totals(weights)
    return cats.get("Equity", 0.0) + cats.get("RealAssets", 0.0)


# ----- Drawdown utility -----
def compute_drawdown(nav: pd.Series) -> pd.Series:
    peaks = nav.cummax()
    return (nav / peaks - 1.0)


# ----- Sidebar disclaimer (shared) -----
DISCLAIMER = (
    "본 대시보드는 자율주행 SAA 파이프라인 결과를 시각화한 정보 제공 목적의 자료이며, "
    "특정 금융상품의 매수·매도 권유가 아닙니다. 백테스트 성과는 가상의 가정에 기반한 것이며 "
    "미래 성과를 보장하지 않습니다. KR DC/IRP 규제 (위험자산 70% 한도)를 가정한 IPS를 사용합니다."
)


def render_sidebar():
    from auth import check_password
    check_password()

    st.sidebar.markdown("### KR 연금 자율주행 SAA")
    st.sidebar.caption("Source: kr_pension_portfolio + kr_pension_hybrid")
    nav_dates = []
    for v in ["baseline", "llm", "v2_baseline", "v2_score", "v2_phase2"]:
        n = load_nav(v)
        if n is not None and not n.empty:
            nav_dates.append((v, n.index.min(), n.index.max()))
    if nav_dates:
        st.sidebar.markdown("**백테스트 기간**")
        for v, lo, hi in nav_dates:
            st.sidebar.text(f"  {v}: {lo.date()} ~ {hi.date()}")
    st.sidebar.markdown("---")
    st.sidebar.markdown("**면책 고지**")
    st.sidebar.caption(DISCLAIMER)
