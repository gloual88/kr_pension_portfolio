# Risk Assessment Skill (CRO)

Reference: Section 3.5 of Ang, Azimbayev, Kim (2026).

The Chief Risk Officer skill produces a standardized risk report for every
candidate portfolio. It does **not vote** — it scores risk and writes commentary.

## Risk Metrics
- ex-ante volatility (= sqrt(w'Σw))
- ex-ante 95% Value-at-Risk (parametric Gaussian)
- backtested historical max drawdown (when returns panel available)
- concentration: HHI on weights, top-3 weight, effective N (Meucci 2009)
- factor tilts: equity beta, duration, credit, FX
- IPS compliance: position bounds, category bounds, expected vol band, MaxDD limit, tracking error vs benchmark

## Output
- `risk_report.json` — quantitative risk metrics + IPS compliance flags.
- `risk_report.md` — narrative for the strategy review packet.
