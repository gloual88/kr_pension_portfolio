# Strategy Review Skill

Reference: Section 3.5 of Ang, Azimbayev, Kim (2026).

## Stages
1. **CRO Risk Report** for every candidate (vol, VaR, MaxDD, concentration, factor tilts, IPS compliance).
2. **Peer Review**: each PC agent reviews exactly 2 peers (1 same-category, 1 cross-category). Random with recorded seed.
3. **Modified Borda Count Voting**:
   - Each agent submits a top-5 ranking (5,4,3,2,1 points; excludes itself).
   - Each agent submits one bottom flag (-2 points).
4. **Quantitative Metric Score** — weighted composite of:
   - backtest Sharpe (25%)
   - IPS compliance (15%)
   - diversification (15%)
   - regime fit (20%)
   - estimation robustness (15%)
   - CMA utilization (10%)
5. **Composite** = regime-dependent blend of vote total and metric score.
6. **Diversity constraint**: top-5 must include ≥3 of 4 families.
7. **Revisions**: top-5 PC agents revise proposals using full-information reviews.
