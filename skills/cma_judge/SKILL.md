# CMA Judge Skill

Reference: Exhibit 4 of Ang, Azimbayev, Kim (2026).

Evaluates multiple CMA methods and selects (or blends) the final expected return.

## Inputs
- `cma_methods.json`        — point estimates + confidence per method.
- `signals.json`            — asset-level macro/technical/valuation signals.
- `macro-view.json`         — current regime, growth, inflation, policy.
- `historical_stats.json`   — trailing returns, vol, drawdowns.

## Seven Candidate Methods (equity)
1. **Historical ERP + Rf** — long-run realized equity premium.
2. **Regime-Adjusted** — conditional premium for current macro regime.
3. **BL Equilibrium** — market-implied return from cap weights.
4. **Inverse Gordon** — yield + growth from current valuation.
5. **Implied ERP (CAPE)** — earnings yield as return proxy.
6. **Survey/Analyst** — consensus or macro-agent view.
7. **Auto-Blend** — confidence-weighted average of methods 1–6.

## Five Methods (fixed income / real assets)
1. Yield carry
2. Roll-down enhanced yield
3. Term-premium adjusted
4. Regime-adjusted
5. Auto-blend

## Judgment Rules
1. Assess dispersion (tight <3pp / moderate 3-6pp / wide >6pp).
2. Apply regime logic.
3. Check valuation context.
4. Check signal alignment.
5. Select — pick one, define custom weights, or accept the blend.

**Hard constraint:** the final estimate MUST lie within `[min, max]` of the candidates.
