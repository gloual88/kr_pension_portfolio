# Meta-Learning Skill

Reference: Section 5.3 of Ang, Azimbayev, Kim (2026).

The meta-agent runs a self-improvement cycle after each rebalancing period:

1. **Feedback collection** — compare the macro agent's regime calls and every
   AC-agent's CMA against realized returns over a rolling 3-year window.
2. **Diagnostics** — compute regime accuracy, cross-sectional rank correlation
   of expected returns vs realized, signal hit rates, per-method prediction
   error by asset class and regime.
3. **Improvement search** — propose targeted modifications:
   - down-weight a CMA method that systematically over-estimates in late-cycle.
   - update the CMA judge to apply a larger valuation tilt above CAPE thresholds.
   - rebalance peer-review weights when a category's voting drift correlates
     with weak realized performance.
4. **Auto-modification** — write change records to `meta/changelog.json` with
   evidence base, reasoning, and exact (logical) modifications.

Note: in this offline implementation we *log* the proposed changes but do not
overwrite live agent files. A production deployment would enable that step
behind sandboxing as discussed in Section 5.1.
