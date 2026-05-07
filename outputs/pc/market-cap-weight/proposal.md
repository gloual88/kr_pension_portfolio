# PC Proposal — Market-Cap Weight

**Category:** A_Heuristic  
**Method:** `market_cap_weight`

## Top Weights

| Asset class | Weight |
|-------------|--------|
| us-large-cap | 20.2% |
| intl-developed | 7.8% |
| kr-treasuries-10y | 5.2% |
| kr-short-bonds | 5.2% |
| kr-credit | 5.2% |
| us-treasuries-10y | 5.2% |
| us-treasuries-30y | 5.2% |
| us-ig-credit | 5.2% |

## Diagnostics

- E[r]: 5.31%, σ: 8.26%
- Backtest Sharpe: 2.02, MaxDD: -8.6%
- Effective N: 12.3, Top-3 weight: 33%
- IPS compliance: 0.90 (flags: 1)
- Diversification score: 0.25
- Regime fit: 0.50
- Estimation robustness: 0.55
- CMA utilization: +0.04