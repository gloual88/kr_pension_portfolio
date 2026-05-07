# Strategy Review

## Borda Count Vote Tally (composite ranking)

| Rank | Method | Category | Vote pts | Composite |
|-----:|--------|----------|---------:|----------:|
| 1 | Maximum Diversification | C_RiskStructured | 79 | 0.989 |
| 2 | Risk Parity | C_RiskStructured | 73 | 0.965 |
| 3 | Hierarchical Risk Parity | C_RiskStructured | 66 | 0.874 |
| 4 | Tail Risk Parity | D_NonTraditional | 36 | 0.632 |
| 5 | Maximum Entropy | E_Researcher | 24 | 0.515 |
| 6 | Black-Litterman | B_ReturnOptimized | 20 | 0.510 |
| 7 | Equal Weight (1/N) | A_Heuristic | 10 | 0.386 |
| 8 | Inverse Variance | A_Heuristic | 4 | 0.314 |
| 9 | Inverse Volatility | A_Heuristic | 2 | 0.309 |
| 10 | Volatility Targeting | A_Heuristic | 1 | 0.257 |
| 11 | Minimum Correlation | C_RiskStructured | -2 | 0.220 |
| 12 | Total Portfolio Allocation (two-factor) | D_NonTraditional | -2 | 0.212 |
| 13 | Robust Mean-Variance | B_ReturnOptimized | 0 | 0.180 |
| 14 | CVaR Minimization | D_NonTraditional | -4 | 0.165 |
| 15 | Global Minimum Variance | C_RiskStructured | 0 | 0.165 |
| 16 | Market-Cap Weight | A_Heuristic | -4 | 0.157 |
| 17 | Max Drawdown Constrained | D_NonTraditional | -4 | 0.147 |
| 18 | Resampled Efficient Frontier | B_ReturnOptimized | 0 | 0.140 |
| 19 | Mean-Downside Risk (Sortino) | B_ReturnOptimized | 0 | 0.085 |
| 20 | Maximum Sharpe Ratio | B_ReturnOptimized | -14 | 0.025 |
| 21 | Adversarial Diversifier | D_NonTraditional | -12 | 0.012 |

## Sample peer reviews (target → reviewers)

### equal-weight
- **market-cap-weight** (same): verdict=approve, score=0.67
- **volatility-targeting** (same): verdict=approve, score=0.67
- **cvar-min** (cross): verdict=approve, score=0.70

### market-cap-weight
- **equal-weight** (same): verdict=approve, score=0.63

### inverse-volatility
- **risk-parity** (cross): verdict=approve, score=0.69
- **hrp** (cross): verdict=approve, score=0.69

### inverse-variance
- **adversarial-diversifier** (cross): verdict=approve, score=0.69

### volatility-targeting
- **inverse-volatility** (same): verdict=approve, score=0.65
- **inverse-variance** (same): verdict=approve, score=0.65
- **min-correlation** (cross): verdict=approve, score=0.68

### max-sharpe
- **black-litterman** (same): verdict=approve, score=0.61
- **robust-mv** (same): verdict=approve, score=0.61
