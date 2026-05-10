# Asset Class — Money Market Active

**Slug:** `money-market`  
**Category:** Cash  
**ETF:** 357870  
**Regime context:** late-cycle (P(rec) 20%)  
**Yield-curve context:** bear-parallel

## CMA Decision

- Expected return (3y, nominal): **4.35%**
- Expected volatility (annualized): **1.58%**
- Dispersion across methods: tight
- Rationale: Dispersion tight (0.5pp). Non-equity: lean on yield/regime adjusted blend.

### Method weights (judge)

| Method | Weight | Estimate |
|--------|--------|----------|
| yield_carry | 10% | 4.00% |
| rolldown_enhanced | 0% | 4.00% |
| term_premium_adj | 0% | 4.50% |
| regime_adjusted | 50% | 4.50% |
| auto_blend | 40% | 4.24% |

## Historical Statistics (annualized)

- Mean: 3.34%
- Volatility: 1.58%
- Sharpe: 2.11
- Max drawdown: -0.0%

## Signals

- macro: -0.59
- momentum: +0.07
- trend: +0.04
- mean_reversion: -0.83
- sentiment: -0.19
- composite: -0.30