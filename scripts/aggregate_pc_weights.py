"""
aggregate_pc_weights.py
========================
21개 PC 모델의 proposal.json을 읽어 ETF×Method 비중 매트릭스로 집계.

실행:
  python -m kr_pension_portfolio.scripts.aggregate_pc_weights \
      --out outputs_trimmed10 --ips ips_trimmed10.yaml
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml


def main(out_dir: str, ips_file: str) -> None:
    base = Path(__file__).resolve().parent.parent
    ips_path = base / "configs" / ips_file
    pc_cfg_path = base / "configs" / "pc_agents.yaml"
    out_path = base / out_dir

    with open(ips_path, "r", encoding="utf-8") as f:
        ips = yaml.safe_load(f)
    with open(pc_cfg_path, "r", encoding="utf-8") as f:
        pc_cfg = yaml.safe_load(f)

    asset_classes = ips["investment_universe"]["asset_classes"]
    slugs = [ac["slug"] for ac in asset_classes]
    etf_label = {ac["slug"]: f'{ac["etf"]} {ac["etf_name"]}' for ac in asset_classes}
    cat = {ac["slug"]: ac["category"] for ac in asset_classes}

    rows = []
    for entry in pc_cfg["pc_agents"]:
        method_slug = entry["slug"]
        # 우선 revised → 없으면 그냥 proposal
        prop_path = out_path / "pc" / method_slug / "proposal_revised.json"
        if not prop_path.exists():
            prop_path = out_path / "pc" / method_slug / "proposal.json"
        if not prop_path.exists():
            print(f"[skip] {method_slug}: no proposal at {prop_path}")
            continue
        with open(prop_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        weights = data.get("weights", {})
        rows.append({"method": method_slug, "name": entry["name"],
                     "category": entry["category"], **weights})

    if not rows:
        print("[err] no proposals found.")
        return

    df = pd.DataFrame(rows)
    # ETF 컬럼 순서 정렬
    weight_cols = [s for s in slugs if s in df.columns]
    df = df[["method", "name", "category"] + weight_cols]

    # CSV (% 단위 표기용 사본도 같이)
    csv_raw = out_path / "pc_weights_matrix.csv"
    df.to_csv(csv_raw, index=False, encoding="utf-8-sig")
    print(f"[saved] {csv_raw}")

    df_pct = df.copy()
    for c in weight_cols:
        df_pct[c] = (df_pct[c] * 100).round(2)
    csv_pct = out_path / "pc_weights_matrix_pct.csv"
    df_pct.to_csv(csv_pct, index=False, encoding="utf-8-sig")
    print(f"[saved] {csv_pct}")

    # Transpose view: rows = ETF, cols = method (보기 편함)
    pivot = df.set_index("method")[weight_cols].T
    pivot.index = [f"{s}  [{cat[s]}]  {etf_label[s]}" for s in pivot.index]
    pivot_pct = (pivot * 100).round(2)
    csv_pivot = out_path / "pc_weights_matrix_pivot_pct.csv"
    pivot_pct.to_csv(csv_pivot, encoding="utf-8-sig")
    print(f"[saved] {csv_pivot}")

    # 콘솔 요약 — 각 모델별 카테고리 합계
    print("\n=== 카테고리별 비중 합계 (%) ===")
    cat_sum_rows = []
    for _, r in df.iterrows():
        cs = {"method": r["method"]}
        for c in {"Equity", "FixedIncome", "RealAssets", "Cash"}:
            cs[c] = round(sum(r[s] for s in weight_cols if cat[s] == c) * 100, 1)
        cs["Risky(Eq+Real)"] = round(cs["Equity"] + cs["RealAssets"], 1)
        cat_sum_rows.append(cs)
    cat_sum = pd.DataFrame(cat_sum_rows)
    print(cat_sum.to_string(index=False))

    cat_sum_path = out_path / "pc_category_sums_pct.csv"
    cat_sum.to_csv(cat_sum_path, index=False, encoding="utf-8-sig")
    print(f"\n[saved] {cat_sum_path}")

    # ETF별 평균 비중 (21개 모델 평균)
    print("\n=== ETF별 평균 비중 (21 모델) ===")
    avg = (df[weight_cols].mean() * 100).round(2)
    avg_df = pd.DataFrame({
        "etf": [etf_label[s] for s in avg.index],
        "category": [cat[s] for s in avg.index],
        "mean_weight_%": avg.values,
    })
    avg_df = avg_df.sort_values("mean_weight_%", ascending=False)
    print(avg_df.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="outputs_trimmed10")
    parser.add_argument("--ips", default="ips_trimmed10.yaml")
    args = parser.parse_args()
    main(out_dir=args.out, ips_file=args.ips)
