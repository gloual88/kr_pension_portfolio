# Meta-Agent Feedback

- Trailing window: 756 trading days
- Mean absolute prediction error: **17.34%**
- Cross-sectional rank correlation: **+0.69**

## Per-asset error

| Asset | Forecast | Realized | Error |
|-------|---------:|---------:|------:|
| kr-large-cap | 5.95% | 57.02% | -51.07% |
| kr-dividend | 5.95% | 39.66% | -33.72% |
| us-large-cap | 6.08% | 29.05% | -22.97% |
| us-tech | 5.95% | 39.66% | -33.70% |
| kr-treasuries-10y | 4.35% | 2.57% | +1.78% |
| us-treasuries-10y | 4.35% | 5.45% | -1.10% |
| us-ig-credit | 4.35% | 6.43% | -2.08% |
| gold | 6.18% | 30.91% | -24.73% |
| kofr-cash | 4.35% | 3.42% | +0.93% |
| money-market | 4.35% | 3.03% | +1.32% |

## Proposed Self-Modifications (logged, not executed)

- **skills/cma_judge/SKILL.md** — Strengthen valuation tilt rule: PE>28 -> +0.10 valuation weight.  
  _Reason: Mean absolute prediction error 17.34% exceeds 6% threshold._
- **agents/asset_class_agent.py** — Add post-judge cap of +200bp above auto-blend for: ['kr-treasuries-10y', 'money-market', 'kofr-cash'].  
  _Reason: Top-3 over-forecast list shows persistent positive bias._