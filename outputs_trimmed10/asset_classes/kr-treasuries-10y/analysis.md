# Asset Class — KR Treasuries 10Y

**Slug:** `kr-treasuries-10y`  
**Category:** FixedIncome  
**ETF:** 152380  
**Regime context:** late-cycle (P(rec) 20%)  
**Yield-curve context:** bear-parallel

## CMA Decision

- Expected return (3y, nominal): **4.35%**
- Expected volatility (annualized): **5.43%**
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

- Mean: 2.19%
- Volatility: 5.43%
- Sharpe: 0.40
- Max drawdown: -21.3%

## Signals

- macro: -0.27
- momentum: -0.11
- trend: -0.11
- mean_reversion: +0.79
- sentiment: -0.24
- composite: +0.01