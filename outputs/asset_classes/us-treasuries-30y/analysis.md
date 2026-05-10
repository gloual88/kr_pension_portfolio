# Asset Class — US Treasuries Ultra 30Y (H)

**Slug:** `us-treasuries-30y`  
**Category:** FixedIncome  
**ETF:** 304660  
**Regime context:** late-cycle (P(rec) 20%)  
**Yield-curve context:** bear-parallel

## CMA Decision

- Expected return (3y, nominal): **4.35%**
- Expected volatility (annualized): **14.05%**
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

- Mean: 3.85%
- Volatility: 14.05%
- Sharpe: 0.27
- Max drawdown: -52.6%

## Signals

- macro: -0.29
- momentum: -0.06
- trend: -0.04
- mean_reversion: +0.45
- sentiment: +0.02
- composite: +0.02