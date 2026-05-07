# Historical Analysis Skill

Provides reusable functions for loading returns, computing risk/return statistics,
drawdown profiles, rolling statistics, and pairwise correlations.

## Functions

- `summary_stats(returns)` — annualized mean, vol, Sharpe, skew, kurtosis, max drawdown.
- `rolling_volatility(returns, window)` — rolling annualized vol.
- `correlation_matrix(returns, halflife=None)` — optional EWMA half-life.
- `historical_erp(returns, rf_returns)` — long-run equity premium.
- `drawdown_profile(returns)` — DD series + DD duration.
