# Strategy Review

## Borda Count Vote Tally (composite ranking)

| Rank | Method | Category | Vote pts | Composite |
|-----:|--------|----------|---------:|----------:|
| 1 | Maximum Diversification | C_RiskStructured | 84 | 1.000 |
| 2 | Risk Parity | C_RiskStructured | 63 | 0.845 |
| 3 | Hierarchical Risk Parity | C_RiskStructured | 54 | 0.748 |
| 4 | Tail Risk Parity | D_NonTraditional | 43 | 0.674 |
| 5 | Black-Litterman | B_ReturnOptimized | 31 | 0.587 |
| 6 | Maximum Entropy | E_Researcher | 26 | 0.538 |
| 7 | Equal Weight (1/N) | A_Heuristic | 13 | 0.422 |
| 8 | Inverse Variance | A_Heuristic | 1 | 0.273 |
| 9 | CVaR Minimization | D_NonTraditional | -2 | 0.208 |
| 10 | Minimum Correlation | C_RiskStructured | -2 | 0.204 |
| 11 | Robust Mean-Variance | B_ReturnOptimized | 0 | 0.197 |
| 12 | Inverse Volatility | A_Heuristic | 0 | 0.192 |
| 13 | Global Minimum Variance | C_RiskStructured | 0 | 0.172 |
| 14 | Resampled Efficient Frontier | B_ReturnOptimized | 0 | 0.156 |
| 15 | Total Portfolio Allocation (two-factor) | D_NonTraditional | 0 | 0.150 |
| 16 | Market-Cap Weight | A_Heuristic | -4 | 0.148 |
| 17 | Volatility Targeting | A_Heuristic | 0 | 0.148 |
| 18 | Maximum Sharpe Ratio | B_ReturnOptimized | -8 | 0.088 |
| 19 | Mean-Downside Risk (Sortino) | B_ReturnOptimized | 0 | 0.076 |
| 20 | Adversarial Diversifier | D_NonTraditional | -10 | 0.033 |
| 21 | Max Drawdown Constrained | D_NonTraditional | -16 | 0.029 |

## Sample peer reviews (target → reviewers)

### equal-weight
- **market-cap-weight** (same): verdict=approve, score=0.70
- **volatility-targeting** (same): verdict=approve, score=0.70
- **cvar-min** (cross): verdict=approve, score=0.73

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
- **black-litterman** (same): verdict=approve, score=0.63
- **robust-mv** (same): verdict=approve, score=0.63
