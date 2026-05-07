# Meta-Agent Feedback

- Trailing window: 756 trading days
- Mean absolute prediction error: **16.28%**
- Cross-sectional rank correlation: **+0.69**

## Per-asset error

| Asset | Forecast | Realized | Error |
|-------|---------:|---------:|------:|
| kr-large-cap | 5.95% | 51.94% | -45.99% |
| kr-dividend | 5.95% | 38.55% | -32.61% |
| us-large-cap | 6.08% | 27.81% | -21.73% |
| us-tech | 5.95% | 37.30% | -31.34% |
| kr-treasuries-10y | 4.35% | 1.65% | +2.69% |
| us-treasuries-10y | 4.35% | 5.21% | -0.86% |
| us-ig-credit | 4.35% | 6.00% | -1.65% |
| gold | 6.18% | 29.83% | -23.65% |
| kofr-cash | 4.35% | 3.42% | +0.92% |
| money-market | 4.35% | 3.01% | +1.33% |

## Proposed Self-Modifications (logged, not executed)

- **skills/cma_judge/SKILL.md** — Strengthen valuation tilt rule: PE>28 -> +0.10 valuation weight.  
  _Reason: Mean absolute prediction error 16.28% exceeds 6% threshold._
- **agents/asset_class_agent.py** — Add post-judge cap of +200bp above auto-blend for: ['kr-treasuries-10y', 'money-market', 'kofr-cash'].  
  _Reason: Top-3 over-forecast list shows persistent positive bias._