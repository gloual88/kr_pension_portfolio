# Ensemble Combination Skill

Reference: Section 3.6 of Ang, Azimbayev, Kim (2026).

## Seven CIO Ensemble Methods
1. **Simple average**         — equal weight across all surviving PCs.
2. **Inverse tracking-error** — weight ∝ 1 / TE vs centroid (paper's choice).
3. **Backtest-Sharpe weight** — weight ∝ backtest Sharpe.
4. **Meta-optimization**      — treat PC portfolios as “assets” and re-optimize.
5. **Regime-conditional**     — vary weights by macro regime (table).
6. **Composite-score weight** — weight ∝ composite score from strategy review.
7. **Trimmed mean**           — drop top/bottom outliers, then average.

The CIO scores each ensemble on the same diagnostic suite and selects the one
best suited to the current regime, with a written rationale.
