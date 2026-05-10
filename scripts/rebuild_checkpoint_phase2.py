"""One-off: reconstruct quarter_runs.jsonl from already-saved quarter dirs.

Used to resume a Phase 2 backtest after segfault without re-paying LLM cost.
"""
from __future__ import annotations
import json
from pathlib import Path

base = Path(__file__).resolve().parents[1]
out_path = base / "outputs" / "backtest_kr_lock70_llm_phase2"
quarters_dir = out_path / "quarters"
checkpoint = out_path / "quarter_runs.jsonl"

records = []
for qdir in sorted(quarters_dir.iterdir()):
    if not qdir.is_dir():
        continue
    cio_file = qdir / "cio" / "final_portfolio.json"
    macro_file = qdir / "macro" / "macro-view.json"
    if not (cio_file.exists() and macro_file.exists()):
        print(f"SKIP {qdir.name}: missing cio or macro output")
        continue
    with open(cio_file, "r", encoding="utf-8") as f:
        cio = json.load(f)
    with open(macro_file, "r", encoding="utf-8") as f:
        macro = json.load(f)

    rec = {
        "as_of": qdir.name + "T00:00:00",
        "skipped": False,
        "regime": macro.get("regime"),
        "regime_conf": macro.get("confidence"),
        "p_rec": macro.get("recession_probability_12m"),
        "chosen_ensemble": cio.get("chosen_ensemble"),
        "weights": cio.get("weights", {}),
        "metrics": cio.get("metrics", {}),
    }
    records.append(rec)

with open(checkpoint, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, default=float) + "\n")

print(f"Wrote {len(records)} records to {checkpoint}")
for r in records:
    print(f"  {r['as_of'][:10]} regime={r['regime']:<11} ens={r['chosen_ensemble']}")
