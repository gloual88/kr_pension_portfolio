# PC Proposal — Market-Cap Weight

**Category:** A_Heuristic  
**Method:** `market_cap_weight`

## Top Weights

| Asset class | Weight |
|-------------|--------|
| us-large-cap | 24.0% |
| gold | 15.0% |
| kr-large-cap | 10.3% |
| kr-dividend | 10.3% |
| us-tech | 10.3% |
| kr-treasuries-10y | 8.4% |
| us-treasuries-10y | 8.4% |
| us-ig-credit | 8.4% |

## Diagnostics

- E[r]: 5.53%, σ: 8.88%
- Backtest Sharpe: 2.46, MaxDD: -8.2%
- Effective N: 7.4, Top-3 weight: 49%
- IPS compliance: 0.90 (flags: 1)
- Diversification score: 0.36
- Regime fit: 0.50
- Estimation robustness: 0.55
- CMA utilization: +0.13