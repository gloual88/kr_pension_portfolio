# Signal Generation Skill

Generates per-asset-class signals across four buckets:
- **Macro**       — sensitivity dot product with current regime scores.
- **Technical**   — momentum (12-1), trend (50d/200d MA), mean reversion z-score.
- **Valuation**   — equity: CAPE, P/E, ERP; bonds: yield vs 5y avg, OAS vs 5y avg.
- **Sentiment**   — fund flows / positioning proxy.

Every signal is normalised to [-1, +1] and tagged with a confidence weight. The
asset-class agent passes these to the CMA judge and folds them into the
analysis report.
