# Asset Class — KR Short Term Bonds (MSB)

**Slug:** `kr-short-bonds`  
**Category:** FixedIncome  
**ETF:** 157450  
**Regime context:** late-cycle (P(rec) 20%)  
**Yield-curve context:** bear-parallel

## CMA Decision

- Expected return (3y, nominal): **4.35%**
- Expected volatility (annualized): **10.16%**
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

- Mean: 2.40%
- Volatility: 10.16%
- Sharpe: 0.24
- Max drawdown: -23.1%

## Signals

- macro: -0.04
- momentum: +0.06
- trend: +0.03
- mean_reversion: -0.81
- sentiment: -0.03
- composite: -0.16