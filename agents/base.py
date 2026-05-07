"""
Base agent abstraction.

Per Section 3.2 of the paper, every agent is defined by four components:
    1. description    (markdown / docstring)
    2. scripts        (Python computation)
    3. skills         (reusable knowledge modules)
    4. output contract (JSON schemas + markdown reports)

We capture this contract in BaseAgent. Concrete agents subclass and override
`run()`, which must produce both:
  - a JSON file (machine-consumed downstream)
  - a markdown report (human audit trail)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AgentContext:
    """Shared state passed through the pipeline."""
    output_root: Path
    config: Dict[str, Any]
    artifacts: Dict[str, Any] = field(default_factory=dict)

    def save_json(self, relpath: str, payload: Any) -> Path:
        full = self.output_root / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=_json_default)
        return full

    def save_md(self, relpath: str, text: str) -> Path:
        full = self.output_root / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
        return full

    def load_json(self, relpath: str) -> Any:
        with open(self.output_root / relpath, "r", encoding="utf-8") as f:
            return json.load(f)


def _json_default(o: Any) -> Any:
    import numpy as np
    import pandas as pd
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    if isinstance(o, pd.DataFrame):
        return o.to_dict(orient="list")
    if isinstance(o, pd.Series):
        return o.to_dict()
    raise TypeError(f"{type(o).__name__} is not JSON serializable")


@dataclass
class AgentSpec:
    slug: str
    role: str
    skills: List[str]
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


class BaseAgent:
    SPEC: AgentSpec  # subclass must set

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def log(self, msg: str) -> None:
        # Lightweight stdout log so the pipeline shows progress.
        print(f"[{self.SPEC.slug}] {msg}")
