# PC Proposal — Market-Cap Weight

**Category:** A_Heuristic  
**Method:** `market_cap_weight`

## Top Weights

| Asset class | Weight |
|-------------|--------|
| us-large-cap | 25.0% |
| kr-large-cap | 9.0% |
| kr-dividend | 9.0% |
| us-tech | 9.0% |
| kr-treasuries-10y | 9.0% |
| us-treasuries-10y | 9.0% |
| us-ig-credit | 9.0% |
| kofr-cash | 9.0% |

## Diagnostics

- E[r]: 5.26%, σ: 7.89%
- Backtest Sharpe: 2.28, MaxDD: -8.0%
- Effective N: 7.8, Top-3 weight: 43%
- IPS compliance: 0.90 (flags: 1)
- Diversification score: 0.30
- Regime fit: 0.50
- Estimation robustness: 0.55
- CMA utilization: +0.03