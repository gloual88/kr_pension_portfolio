# Asset Class — US Treasuries 10Y Futures

**Slug:** `us-treasuries-10y`  
**Category:** FixedIncome  
**ETF:** 305080  
**Regime context:** late-cycle (P(rec) 20%)  
**Yield-curve context:** bear-parallel

## CMA Decision

- Expected return (3y, nominal): **4.35%**
- Expected volatility (annualized): **7.67%**
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

- Mean: 4.55%
- Volatility: 7.67%
- Sharpe: 0.59
- Max drawdown: -17.2%

## Signals

- macro: -0.11
- momentum: +0.15
- trend: +0.14
- mean_reversion: -0.37
- sentiment: -0.38
- composite: -0.11