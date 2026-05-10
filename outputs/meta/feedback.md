# Meta-Agent Feedback

- Trailing window: 756 trading days
- Mean absolute prediction error: **14.58%**
- Cross-sectional rank correlation: **+0.67**

## Per-asset error

| Asset | Forecast | Realized | Error |
|-------|---------:|---------:|------:|
| kr-large-cap | 5.95% | 57.37% | -51.42% |
| kr-kosdaq | 5.96% | 20.03% | -14.08% |
| kr-dividend | 5.95% | 40.43% | -34.49% |
| us-large-cap | 6.08% | 28.20% | -22.12% |
| us-tech | 5.95% | 38.19% | -32.23% |
| us-dividend | 5.95% | 18.12% | -12.18% |
| intl-developed | 5.71% | 30.71% | -25.01% |
| emerging-markets | 7.50% | 19.19% | -11.68% |
| kr-treasuries-10y | 4.35% | 2.30% | +2.04% |
| kr-short-bonds | 4.35% | 3.18% | +1.17% |
| kr-credit | 4.35% | 3.28% | +1.07% |
| us-treasuries-10y | 4.35% | 5.25% | -0.90% |
| us-treasuries-30y | 4.35% | -4.77% | +9.12% |
| us-ig-credit | 4.35% | 6.29% | -1.95% |
| gold | 6.18% | 31.42% | -25.24% |
| commodities | 3.87% | 19.42% | -15.55% |
| kofr-cash | 4.35% | 3.39% | +0.95% |
| money-market | 4.35% | 3.03% | +1.32% |

## Proposed Self-Modifications (logged, not executed)

- **skills/cma_judge/SKILL.md** — Strengthen valuation tilt rule: PE>28 -> +0.10 valuation weight.  
  _Reason: Mean absolute prediction error 14.58% exceeds 6% threshold._
- **agents/asset_class_agent.py** — Add post-judge cap of +200bp above auto-blend for: ['us-treasuries-30y', 'kr-treasuries-10y', 'money-market'].  
  _Reason: Top-3 over-forecast list shows persistent positive bias._