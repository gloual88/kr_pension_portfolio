# PC Proposal — Black-Litterman

**Category:** B_ReturnOptimized  
**Method:** `black_litterman`

## Top Weights

| Asset class | Weight |
|-------------|--------|
| us-treasuries-30y | 8.7% |
| us-ig-credit | 7.3% |
| us-dividend | 7.0% |
| kr-short-bonds | 6.9% |
| us-treasuries-10y | 6.8% |
| gold | 6.8% |
| kr-large-cap | 6.0% |
| kr-dividend | 5.8% |

## Diagnostics

- E[r]: 5.30%, σ: 7.12%
- Backtest Sharpe: 2.13, MaxDD: -6.9%
- Effective N: 16.6, Top-3 weight: 23%
- IPS compliance: 0.90 (flags: 1)
- Diversification score: 0.36
- Regime fit: 0.75
- Estimation robustness: 0.65
- CMA utilization: +0.01