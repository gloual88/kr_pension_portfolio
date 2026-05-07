# Portfolio Construction Methods Skill

Implements the 20 canonical methods from Exhibit 5 plus the PC-Researcher's
maximum-entropy proposal (March 2026 run).

All methods take `(mu, Sigma, ips_constraints)` and return a weight vector `w`
that sums to 1 and respects min/max bounds and category bounds.

| # | Method                            | Family            |
|---|-----------------------------------|-------------------|
| 1 | Equal weight (1/N)                | A: Heuristic      |
| 2 | Market-cap weight                 | A: Heuristic      |
| 3 | Inverse volatility                | A: Heuristic      |
| 4 | Inverse variance                  | A: Heuristic      |
| 5 | Volatility targeting              | A: Heuristic      |
| 6 | Maximum Sharpe ratio              | B: Return-Optim   |
| 7 | Black-Litterman                   | B: Return-Optim   |
| 8 | Robust mean-variance              | B: Return-Optim   |
| 9 | Resampled efficient frontier      | B: Return-Optim   |
|10 | Mean-downside risk (Sortino)      | B: Return-Optim   |
|11 | Global minimum variance           | C: Risk-Struct    |
|12 | Risk parity (ERC)                 | C: Risk-Struct    |
|13 | Hierarchical risk parity (HRP)    | C: Risk-Struct    |
|14 | Maximum diversification           | C: Risk-Struct    |
|15 | Minimum correlation               | C: Risk-Struct    |
|16 | CVaR optimization                 | D: Non-Trad       |
|17 | Max drawdown-constrained          | D: Non-Trad       |
|18 | Tail-risk parity                  | D: Non-Trad       |
|19 | Total Portfolio Allocation 2-fac  | D: Non-Trad       |
|20 | Adversarial diversifier           | D: Non-Trad       |
|21 | Maximum entropy (Researcher)      | E: Researcher     |

`pc_engine.py` is the dispatch table that all PC agents call into.
