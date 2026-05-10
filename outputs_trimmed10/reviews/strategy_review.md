# Strategy Review

## Borda Count Vote Tally (composite ranking)

| Rank | Method | Category | Vote pts | Composite |
|-----:|--------|----------|---------:|----------:|
| 1 | Maximum Diversification | C_RiskStructured | 80 | 0.994 |
| 2 | Risk Parity | C_RiskStructured | 74 | 0.965 |
| 3 | Hierarchical Risk Parity | C_RiskStructured | 66 | 0.872 |
| 4 | Tail Risk Parity | D_NonTraditional | 35 | 0.618 |
| 5 | Black-Litterman | B_ReturnOptimized | 19 | 0.500 |
| 6 | Maximum Entropy | E_Researcher | 21 | 0.497 |
| 7 | Equal Weight (1/N) | A_Heuristic | 10 | 0.387 |
| 8 | Inverse Volatility | A_Heuristic | 3 | 0.322 |
| 9 | Inverse Variance | A_Heuristic | 4 | 0.318 |
| 10 | Volatility Targeting | A_Heuristic | 2 | 0.271 |
| 11 | Global Minimum Variance | C_RiskStructured | 1 | 0.261 |
| 12 | Minimum Correlation | C_RiskStructured | -2 | 0.227 |
| 13 | Total Portfolio Allocation (two-factor) | D_NonTraditional | -2 | 0.224 |
| 14 | Max Drawdown Constrained | D_NonTraditional | -2 | 0.181 |
| 15 | Robust Mean-Variance | B_ReturnOptimized | 0 | 0.180 |
| 16 | CVaR Minimization | D_NonTraditional | -4 | 0.168 |
| 17 | Market-Cap Weight | A_Heuristic | -4 | 0.165 |
| 18 | Mean-Downside Risk (Sortino) | B_ReturnOptimized | -2 | 0.154 |
| 19 | Resampled Efficient Frontier | B_ReturnOptimized | 0 | 0.150 |
| 20 | Maximum Sharpe Ratio | B_ReturnOptimized | -14 | 0.036 |
| 21 | Adversarial Diversifier | D_NonTraditional | -12 | 0.012 |

## Sample peer reviews (target → reviewers)

### equal-weight
- **market-cap-weight** (same): verdict=approve, score=0.69
- **volatility-targeting** (same): verdict=approve, score=0.69
- **cvar-min** (cross): verdict=approve, score=0.72

### market-cap-weight
- **equal-weight** (same): verdict=approve, score=0.65

### inverse-volatility
- **risk-parity** (cross): verdict=approve, score=0.72
- **hrp** (cross): verdict=approve, score=0.72

### inverse-variance
- **adversarial-diversifier** (cross): verdict=approve, score=0.71

### volatility-targeting
- **inverse-volatility** (same): verdict=approve, score=0.67
- **inverse-variance** (same): verdict=approve, score=0.67
- **min-correlation** (cross): verdict=approve, score=0.70

### max-sharpe
- **black-litterman** (same): verdict=approve, score=0.63
- **robust-mv** (same): verdict=approve, score=0.63
