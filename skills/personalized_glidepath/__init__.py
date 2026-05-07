"""Personalized glide-path adapter (Yuanta dynamic glide-path → KR pension SAA).

PoC scope:
- Yuanta stock/bond/cash 3-category targets → KR pension 4-category mapping
- TDF safe-valve to bypass DC/IRP 70% risky-asset cap when target stock > IPS Equity max
- Output: category-level allocation + TDF holding for downstream pipeline / dashboard
"""
from .adapter import (
    AllocationBreakdown,
    GlidePathInputs,
    TDFInputs,
    build_personalized_ips,
    compose_with_tdf,
    compute_personalized_allocation,
    load_personalized_result,
    run_personalized_pipeline,
    run_yuanta_glidepath,
    save_personalized_ips,
    PERSONALIZED_OUT_DIR,
    PERSONALIZED_IPS_FILENAME,
)

__all__ = [
    "AllocationBreakdown",
    "GlidePathInputs",
    "TDFInputs",
    "build_personalized_ips",
    "compose_with_tdf",
    "compute_personalized_allocation",
    "load_personalized_result",
    "run_personalized_pipeline",
    "run_yuanta_glidepath",
    "save_personalized_ips",
    "PERSONALIZED_OUT_DIR",
    "PERSONALIZED_IPS_FILENAME",
]
