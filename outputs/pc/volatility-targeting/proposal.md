# PC Proposal — Volatility Targeting

**Category:** A_Heuristic  
**Method:** `volatility_targeting`

## Top Weights

| Asset class | Weight |
|-------------|--------|
| kofr-cash | 18.0% |
| kr-credit | 14.0% |
| money-market | 12.0% |
| kr-treasuries-10y | 8.0% |
| us-treasuries-10y | 5.7% |
| us-ig-credit | 4.6% |
| kr-short-bonds | 4.3% |
| us-dividend | 4.0% |

## Diagnostics

- E[r]: 4.85%, σ: 4.15%
- Backtest Sharpe: 2.31, MaxDD: -3.8%
- Effective N: 11.0, Top-3 weight: 44%
- IPS compliance: 0.80 (flags: 2)
- Diversification score: 0.38
- Regime fit: 0.50
- Estimation robustness: 0.70
- CMA utilization: -0.14