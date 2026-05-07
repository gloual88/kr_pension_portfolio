"""
Covariance Agent.

Section 3.1 step 3: estimates the asset-class covariance matrix using historical
data and macro forecasts. Uses an EWMA-shrunk sample covariance and adjusts the
diagonal toward the AC agents' expected volatilities so PC agents see a
self-consistent (mu, Sigma) pair.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from .base import AgentContext, AgentSpec, BaseAgent


class CovarianceAgent(BaseAgent):
    SPEC = AgentSpec(
        slug="covariance-agent",
        role="Estimates the asset-class covariance matrix.",
        skills=["historical_analysis", "covariance_estimation"],
    )

    def __init__(self, ctx: AgentContext, returns: pd.DataFrame):
        super().__init__(ctx)
        self.returns = returns

    def run(self) -> Dict[str, Any]:
        slugs = list(self.returns.columns)
        ann = 252
        # Sample covariance + Ledoit-Wolf-like shrinkage to a constant-correlation matrix.
        sample = self.returns.cov().values * ann
        n = sample.shape[0]
        avg_var = float(np.mean(np.diag(sample)))
        avg_corr = float(self.returns.corr().values[np.triu_indices(n, 1)].mean())
        F = avg_var * (avg_corr * np.ones((n, n)) + (1 - avg_corr) * np.eye(n))
        shrink = 0.2
        Sigma = (1 - shrink) * sample + shrink * F

        # Re-anchor diagonal to the AC agents' expected vol if available.
        ac_cma = self.ctx.artifacts.get("ac_cma") or {}
        vols = np.sqrt(np.diag(Sigma))
        for i, slug in enumerate(slugs):
            payload = ac_cma.get(slug)
            if payload and payload.get("expected_volatility", 0) > 0:
                vols[i] = float(payload["expected_volatility"])
        # rebuild covariance using corr × vols
        D = np.diag(vols)
        old_vols = np.sqrt(np.diag(Sigma))
        corr = Sigma / np.outer(old_vols, old_vols)
        np.fill_diagonal(corr, 1.0)
        Sigma_new = D @ corr @ D
        # Ensure symmetric and positive definite.
        Sigma_new = 0.5 * (Sigma_new + Sigma_new.T)
        eigvals = np.linalg.eigvalsh(Sigma_new)
        if eigvals.min() < 1e-8:
            Sigma_new = Sigma_new + (1e-6 - eigvals.min()) * np.eye(n)

        payload = {
            "asset_classes": slugs,
            "covariance": Sigma_new.tolist(),
            "correlation": corr.tolist(),
            "volatilities": vols.tolist(),
            "shrinkage": shrink,
        }
        self.ctx.save_json("covariance/cov.json", payload)
        # Markdown summary
        md = ["# Covariance Matrix", "",
              f"Shrinkage to constant-correlation prior: {shrink:.0%}",
              "",
              f"Average vol: {np.mean(vols):.2%}, average correlation: {avg_corr:.2f}",
              "", "## Volatilities", ""]
        for s, v in zip(slugs, vols):
            md.append(f"- {s}: {v:.2%}")
        self.ctx.save_md("covariance/analysis.md", "\n".join(md))

        self.ctx.artifacts["covariance"] = {
            "Sigma": Sigma_new,
            "correlation": corr,
            "vols": vols,
            "slugs": slugs,
        }
        self.log(f"Σ shape={Sigma_new.shape}, mean vol={np.mean(vols):.2%}")
        return payload
