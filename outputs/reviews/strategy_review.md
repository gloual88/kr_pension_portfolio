# Strategy Review

## Borda Count Vote Tally (composite ranking)

| Rank | Method | Category | Vote pts | Composite |
|-----:|--------|----------|---------:|----------:|
| 1 | Risk Parity | C_RiskStructured | 75 | 0.994 |
| 2 | Maximum Diversification | C_RiskStructured | 76 | 0.992 |
| 3 | Hierarchical Risk Parity | C_RiskStructured | 54 | 0.813 |
| 4 | Tail Risk Parity | D_NonTraditional | 43 | 0.725 |
| 5 | Black-Litterman | B_ReturnOptimized | 28 | 0.623 |
| 6 | Maximum Entropy | E_Researcher | 24 | 0.571 |
| 7 | Equal Weight (1/N) | A_Heuristic | 13 | 0.466 |
| 8 | Inverse Variance | A_Heuristic | 2 | 0.338 |
| 9 | Minimum Correlation | C_RiskStructured | -2 | 0.268 |
| 10 | Total Portfolio Allocation (two-factor) | D_NonTraditional | -2 | 0.248 |
| 11 | Inverse Volatility | A_Heuristic | 0 | 0.225 |
| 12 | Robust Mean-Variance | B_ReturnOptimized | 0 | 0.209 |
| 13 | Max Drawdown Constrained | D_NonTraditional | -4 | 0.185 |
| 14 | Volatility Targeting | A_Heuristic | 0 | 0.185 |
| 15 | Global Minimum Variance | C_RiskStructured | 0 | 0.176 |
| 16 | CVaR Minimization | D_NonTraditional | 0 | 0.163 |
| 17 | Resampled Efficient Frontier | B_ReturnOptimized | 0 | 0.152 |
| 18 | Mean-Downside Risk (Sortino) | B_ReturnOptimized | 0 | 0.152 |
| 19 | Market-Cap Weight | A_Heuristic | 0 | 0.136 |
| 20 | Maximum Sharpe Ratio | B_ReturnOptimized | -18 | 0.051 |
| 21 | Adversarial Diversifier | D_NonTraditional | -16 | 0.012 |

## Sample peer reviews (target → reviewers)

### equal-weight
- **market-cap-weight** (same): verdict=approve, score=0.68
- **volatility-targeting** (same): verdict=approve, score=0.68
- **cvar-min** (cross): verdict=approve, score=0.71

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
- **black-litterman** (same): verdict=approve, score=0.60
- **robust-mv** (same): verdict=approve, score=0.60
