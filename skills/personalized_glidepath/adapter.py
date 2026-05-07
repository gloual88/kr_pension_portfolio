"""TDF-safe-valve adapter from Yuanta glide-path output to KR pension allocation.

Derivation (look-through additive in absolute weights of total):
    direct_eq_abs + T * stock_TDF = target_stock     ... (1)
    Pin direct_eq_abs at IPS Equity max E* when target > E*:
        T = (target_stock - E*) / stock_TDF          ... (2)
    Feasibility:
        E* + T <= 1                                  (room for direct FI/Cash within 1-T)
        T <= tdf_max                                 (safety cap)
    When target_stock <= E*, T = 0 and direct_eq_abs = target_stock.
"""
from __future__ import annotations

import copy
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

# Make Yuanta importable (PoC convenience; productionize via shared package later).
_YUANTA_DIR = Path("d:/파이선/Yuanta")
if str(_YUANTA_DIR) not in sys.path:
    sys.path.insert(0, str(_YUANTA_DIR))


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
@dataclass
class GlidePathInputs:
    age: int
    retirement_age: int
    occupation: str                         # one of Yuanta CashFlowAnalysisEngine.industry_betas
    cashflow_series: List[float]            # past N years of net cashflow (KRW 만원 OK — only ratios matter)
    horizon_years: Optional[int] = None     # default to retirement_age - age + 20

    def horizon(self) -> int:
        return self.horizon_years if self.horizon_years is not None else max(1, self.retirement_age - self.age + 20)


@dataclass
class TDFInputs:
    """User-selected TDF / default-option product.

    `eligible` must be True to bypass the 70% risky cap (적격TDF 한정)."""
    name: str = "default-TDF"
    stock: float = 0.60
    bond: float = 0.35
    real_asset: float = 0.05
    cash: float = 0.00
    eligible: bool = True
    max_holding: float = 0.50               # safety cap on TDF weight

    def normalize(self) -> "TDFInputs":
        s = self.stock + self.bond + self.real_asset + self.cash
        if s <= 0:
            return TDFInputs(self.name, 0.6, 0.35, 0.05, 0.0, self.eligible, self.max_holding)
        return TDFInputs(
            self.name,
            self.stock / s, self.bond / s, self.real_asset / s, self.cash / s,
            self.eligible, self.max_holding,
        )


@dataclass
class AllocationBreakdown:
    """Result of the TDF safe-valve mapping."""
    target_stock: float
    target_bond: float
    target_cash: float
    target_real: float = 0.0

    # Direct ETF portion (sums to 1 - tdf_holding)
    direct_equity: float = 0.0
    direct_fi: float = 0.0
    direct_real: float = 0.0
    direct_cash: float = 0.0

    # TDF
    tdf_holding: float = 0.0
    tdf_internal_saa: Dict[str, float] = field(default_factory=dict)

    # Diagnostics
    feasible: bool = True
    notes: List[str] = field(default_factory=list)
    risky_total: float = 0.0
    risky_cap_breached: bool = False

    def lookthrough(self) -> Dict[str, float]:
        s = self.tdf_internal_saa
        return {
            "Equity":      self.direct_equity + self.tdf_holding * s.get("stock", 0.0),
            "FixedIncome": self.direct_fi    + self.tdf_holding * s.get("bond", 0.0),
            "RealAssets":  self.direct_real  + self.tdf_holding * s.get("real_asset", 0.0),
            "Cash":        self.direct_cash  + self.tdf_holding * s.get("cash", 0.0),
        }


# ---------------------------------------------------------------------------
# Yuanta runner
# ---------------------------------------------------------------------------
def run_yuanta_glidepath(g: GlidePathInputs) -> pd.DataFrame:
    """Run the Yuanta master formula and return a DataFrame with columns
    age / final_allocation / bonds_allocation / cash_allocation (the engine's
    3-category output). Stock/bond/cash sum to 1 per row."""
    from dynamic_glidepath_engine import CashFlowAnalysisEngine
    from dynamic_glidepath_calculator import DynamicGlidePathCalculator

    engine = CashFlowAnalysisEngine()
    calc = DynamicGlidePathCalculator()

    cf_chars = engine.analyze_cashflow_pattern(g.cashflow_series)
    hc = engine.analyze_human_capital(g.occupation, g.age, g.retirement_age)
    end_age = g.age + g.horizon()
    df = calc.calculate_dynamic_glidepath(
        range(g.age, end_age + 1),
        cf_chars, hc,
        events=[],          # PoC: 이벤트 비활성. 다음 단계에서 입력 폼으로 추가
    )
    df.attrs["pattern"] = cf_chars.pattern.value
    df.attrs["stability"] = cf_chars.stability_score
    df.attrs["hc_beta"] = hc.hc_beta
    df.attrs["hc_adjustment"] = hc.hc_adjustment
    df.attrs["confidence"] = cf_chars.confidence_level
    return df


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------
def compute_personalized_allocation(
    target_stock: float,
    target_bond: float,
    target_cash: float,
    tdf: TDFInputs,
    *,
    ips_equity_max: float = 0.55,
    ips_real_max: float = 0.15,
    ips_fi_min: float = 0.20,
    risky_cap: float = 0.70,
    real_share_of_stock: float = 0.0,    # PoC: 0 = stock 전부 Equity. 향후 stock × x → RealAssets로 분배 가능
) -> AllocationBreakdown:
    """Map Yuanta 3-category target to KR pension 4-category direct + TDF.

    PoC simplifications:
      - Yuanta stock → Equity (no automatic split into RealAssets unless real_share_of_stock>0).
      - Yuanta bond → FixedIncome.
      - Yuanta cash → Cash.
      - real_share_of_stock optionally redirects a slice of stock target to RealAssets bucket.
    """
    notes: List[str] = []

    # Optional split: target_real comes from a slice of target_stock.
    target_real = target_stock * real_share_of_stock
    target_stock_only = target_stock - target_real

    tdf = tdf.normalize()
    s_tdf = tdf.stock

    # ---- 1. Determine TDF holding T to satisfy stock target -----------------
    feasible = True
    if not tdf.eligible:
        notes.append("적격TDF 미체크: 70% 위험자산 한도 우회 비활성. Equity는 IPS 한도 내로 클립됨.")
        T = 0.0
        direct_eq_pinned = min(target_stock_only, ips_equity_max)
    elif target_stock_only <= ips_equity_max:
        T = 0.0
        direct_eq_pinned = target_stock_only
    else:
        if s_tdf <= 1e-6:
            notes.append("TDF 내부 주식 비중이 0% — TDF로 추가 주식 노출 불가.")
            T = 0.0
            direct_eq_pinned = ips_equity_max
            feasible = False
        else:
            T_needed = (target_stock_only - ips_equity_max) / s_tdf
            # Feasibility: direct portion (1-T) must fit at least the pinned equity = E_max
            T_room_in_total = max(0.0, 1.0 - ips_equity_max)
            T_max_safe = min(tdf.max_holding, T_room_in_total, 1.0)
            T = min(T_needed, T_max_safe)
            direct_eq_pinned = ips_equity_max
            if T < T_needed - 1e-9:
                shortfall_pp = (T_needed - T) * s_tdf * 100.0
                notes.append(
                    f"TDF 비중 한도 {T_max_safe*100:.0f}%로 클립 — 목표 주식 {shortfall_pp:.1f}pp 미달. "
                    f"한도 상향 또는 더 공격적인 TDF(주식 비중↑) 검토."
                )
                feasible = False

    direct_share = max(0.0, 1.0 - T)

    # ---- 2. Direct portion category fill ------------------------------------
    # direct weights are absolute (of total). They sum to direct_share.
    direct_equity = min(direct_eq_pinned, direct_share)
    remaining = direct_share - direct_equity

    direct_real = min(target_real, ips_real_max, max(0.0, remaining))
    remaining -= direct_real

    direct_fi = min(target_bond - T * tdf.bond, remaining)
    direct_fi = max(direct_fi, 0.0)
    remaining -= direct_fi

    direct_cash = max(0.0, remaining)

    # ---- 3. Risk cap diagnostic --------------------------------------------
    # 적격TDF는 70% cap 예외이므로 TDF는 risky_total에서 제외
    risky_total = direct_equity + direct_real + (T if not tdf.eligible else 0.0) * (s_tdf + tdf.real_asset)
    if risky_total > risky_cap + 1e-6:
        notes.append(f"위험자산 비중 {risky_total*100:.1f}% > 70% — IPS 점검 필요.")

    # FI 하한 점검 — 맞춤형 우선 정책: IPS 하한과 충돌 시 맞춤형 결과를 그대로 적용 (정보성 표시)
    lookthrough_fi = direct_fi + T * tdf.bond
    if lookthrough_fi < ips_fi_min - 1e-6:
        notes.append(
            f"맞춤형 채권 비중 {lookthrough_fi*100:.1f}%가 IPS 기본 하한 {ips_fi_min*100:.0f}% 미만 — "
            f"맞춤형 결과를 우선 적용 (IPS 하한은 다음 단계 personalized IPS 생성 시 맞춤형 값으로 완화 예정)."
        )

    return AllocationBreakdown(
        target_stock=target_stock,
        target_bond=target_bond,
        target_cash=target_cash,
        target_real=target_real,
        direct_equity=direct_equity,
        direct_fi=direct_fi,
        direct_real=direct_real,
        direct_cash=direct_cash,
        tdf_holding=T,
        tdf_internal_saa={
            "stock": tdf.stock, "bond": tdf.bond,
            "real_asset": tdf.real_asset, "cash": tdf.cash,
        },
        feasible=feasible,
        notes=notes,
        risky_total=risky_total,
        risky_cap_breached=(risky_total > risky_cap + 1e-6),
    )


# ---------------------------------------------------------------------------
# Personalized IPS generation + pipeline runner (18 ETF integration)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path("d:/파이선/kr_pension_portfolio")
CONFIGS_DIR = PROJECT_ROOT / "configs"
BASE_IPS_PATH = CONFIGS_DIR / "ips.yaml"
PERSONALIZED_IPS_FILENAME = "ips_personalized.yaml"
PERSONALIZED_OUT_DIR = "outputs_personalized"


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_personalized_ips(
    alloc: AllocationBreakdown,
    *,
    base_ips: Optional[dict] = None,
    tolerance: float = 0.005,
) -> dict:
    """Generate personalized IPS by overriding category_bounds based on adapter output.

    The 18-ETF engine produces weights summing to 1 over the *direct portion*. We pass
    fractions of direct_share = (1 - T) as bounds. After the engine runs, the dashboard
    scales results by (1-T) and appends TDF as a separate line for total composition.

    `tolerance` (±0.5% default) gives the optimizer slight wiggle room around the target
    so PC agents have a feasible region rather than a single point.
    """
    if base_ips is None:
        base_ips = _load_yaml(BASE_IPS_PATH)
    pers = copy.deepcopy(base_ips)

    direct_share = max(1e-6, 1.0 - alloc.tdf_holding)
    fracs = {
        "Equity":      alloc.direct_equity / direct_share,
        "FixedIncome": alloc.direct_fi    / direct_share,
        "RealAssets":  alloc.direct_real  / direct_share,
        "Cash":        alloc.direct_cash  / direct_share,
    }
    # Renormalize to defend against tiny floating-point drift
    s = sum(fracs.values()) or 1.0
    fracs = {k: v / s for k, v in fracs.items()}

    cb = pers.setdefault("constraints", {}).setdefault("category_bounds", {})
    for cat, frac in fracs.items():
        cb[cat] = {
            "min": float(max(0.0, frac - tolerance)),
            "max": float(min(1.0, frac + tolerance)),
        }

    pers["_personalized_metadata"] = {
        "tdf_holding": float(alloc.tdf_holding),
        "tdf_internal_saa": {k: float(v) for k, v in alloc.tdf_internal_saa.items()},
        "target_stock": float(alloc.target_stock),
        "target_bond":  float(alloc.target_bond),
        "target_cash":  float(alloc.target_cash),
        "target_real":  float(alloc.target_real),
        "direct_share": float(direct_share),
        "direct_fractions": {k: float(v) for k, v in fracs.items()},
        "feasible": bool(alloc.feasible),
    }
    return pers


def save_personalized_ips(pers_ips: dict, *, filename: str = PERSONALIZED_IPS_FILENAME) -> Path:
    """Write personalized IPS to configs/ folder. Returns the absolute path."""
    out = CONFIGS_DIR / filename
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(pers_ips, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return out


def run_personalized_pipeline(
    *,
    ips_filename: str = PERSONALIZED_IPS_FILENAME,
    out_dir: str = PERSONALIZED_OUT_DIR,
    prefer_data: str = "yfinance",
) -> Path:
    """Invoke run_pipeline.main with the personalized IPS. Returns output directory."""
    if str(PROJECT_ROOT.parent) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT.parent))
    from kr_pension_portfolio.run_pipeline import main as pipeline_main

    pipeline_main(prefer_data=prefer_data, out_root=out_dir, ips_file=ips_filename)
    return PROJECT_ROOT / out_dir


def load_personalized_result(out_dir: str = PERSONALIZED_OUT_DIR) -> Tuple[Optional[dict], Optional[dict]]:
    """Load (final_portfolio.json, macro-view.json) from the personalized output."""
    base = PROJECT_ROOT / out_dir
    cio_path = base / "cio" / "final_portfolio.json"
    macro_path = base / "macro" / "macro-view.json"
    import json

    cio = json.loads(cio_path.read_text(encoding="utf-8")) if cio_path.exists() else None
    macro = json.loads(macro_path.read_text(encoding="utf-8")) if macro_path.exists() else None
    return cio, macro


def compose_with_tdf(
    direct_weights: Dict[str, float],
    tdf_holding: float,
    tdf_name: str = "TDF",
) -> pd.DataFrame:
    """Scale 18-ETF direct weights by (1-T) and append TDF as a separate line.
    Returns a DataFrame with columns: slug, weight, kind ('direct' or 'tdf')."""
    direct_share = max(0.0, 1.0 - tdf_holding)
    rows = []
    for slug, w in direct_weights.items():
        rows.append({"slug": slug, "weight": float(w) * direct_share, "kind": "direct"})
    if tdf_holding > 1e-9:
        rows.append({"slug": tdf_name, "weight": float(tdf_holding), "kind": "tdf"})
    return pd.DataFrame(rows)

