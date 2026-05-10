# Strategy Review

## Borda Count Vote Tally (composite ranking)

| Rank | Method | Category | Vote pts | Composite |
|-----:|--------|----------|---------:|----------:|
| 1 | Maximum Diversification | C_RiskStructured | 79 | 0.992 |
| 2 | Risk Parity | C_RiskStructured | 72 | 0.959 |
| 3 | Hierarchical Risk Parity | C_RiskStructured | 65 | 0.871 |
| 4 | Tail Risk Parity | D_NonTraditional | 36 | 0.633 |
| 5 | Black-Litterman | B_ReturnOptimized | 22 | 0.525 |
| 6 | Maximum Entropy | E_Researcher | 23 | 0.509 |
| 7 | Equal Weight (1/N) | A_Heuristic | 10 | 0.386 |
| 8 | Inverse Volatility | A_Heuristic | 3 | 0.317 |
| 9 | Inverse Variance | A_Heuristic | 4 | 0.315 |
| 10 | Volatility Targeting | A_Heuristic | 1 | 0.258 |
| 11 | Minimum Correlation | C_RiskStructured | -2 | 0.221 |
| 12 | Total Portfolio Allocation (two-factor) | D_NonTraditional | -2 | 0.210 |
| 13 | Robust Mean-Variance | B_ReturnOptimized | 0 | 0.186 |
| 14 | CVaR Minimization | D_NonTraditional | -2 | 0.176 |
| 15 | Max Drawdown Constrained | D_NonTraditional | -2 | 0.170 |
| 16 | Global Minimum Variance | C_RiskStructured | 0 | 0.162 |
| 17 | Mean-Downside Risk (Sortino) | B_ReturnOptimized | -2 | 0.158 |
| 18 | Market-Cap Weight | A_Heuristic | -6 | 0.144 |
| 19 | Resampled Efficient Frontier | B_ReturnOptimized | 0 | 0.137 |
| 20 | Maximum Sharpe Ratio | B_ReturnOptimized | -14 | 0.021 |
| 21 | Adversarial Diversifier | D_NonTraditional | -12 | 0.012 |

## Sample peer reviews (target → reviewers)

### equal-weight
- **market-cap-weight** (same): verdict=approve, score=0.68
- **volatility-targeting** (same): verdict=approve, score=0.68
- **cvar-min** (cross): verdict=approve, score=0.71

### market-cap-weight
- **equal-weight** (same): verdict=approve, score=0.64

### inverse-volatility
- **risk-parity** (cross): verdict=approve, score=0.70
- **hrp** (cross): verdict=approve, score=0.70

### inverse-variance
- **adversarial-diversifier** (cross): verdict=approve, score=0.70

### volatility-targeting
- **inverse-volatility** (same): verdict=approve, score=0.66
- **inverse-variance** (same): verdict=approve, score=0.66
- **min-correlation** (cross): verdict=approve, score=0.69

### max-sharpe
- **black-litterman** (same): verdict=approve, score=0.61
- **robust-mv** (same): verdict=approve, score=0.61
