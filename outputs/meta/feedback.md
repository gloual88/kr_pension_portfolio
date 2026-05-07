# Meta-Agent Feedback

- Trailing window: 756 trading days
- Mean absolute prediction error: **13.77%**
- Cross-sectional rank correlation: **+0.60**

## Per-asset error

| Asset | Forecast | Realized | Error |
|-------|---------:|---------:|------:|
| kr-large-cap | 5.95% | 51.30% | -45.36% |
| kr-kosdaq | 5.96% | 19.76% | -13.80% |
| kr-dividend | 5.95% | 38.57% | -32.62% |
| us-large-cap | 6.08% | 27.62% | -21.54% |
| us-tech | 5.95% | 36.92% | -30.97% |
| us-dividend | 5.95% | 17.09% | -11.15% |
| intl-developed | 5.71% | 29.74% | -24.03% |
| emerging-markets | 7.50% | 16.68% | -9.17% |
| kr-treasuries-10y | 4.35% | 2.20% | +2.15% |
| kr-short-bonds | 4.35% | 3.18% | +1.16% |
| kr-credit | 4.35% | 3.27% | +1.08% |
| us-treasuries-10y | 4.35% | 5.63% | -1.28% |
| us-treasuries-30y | 4.35% | -5.08% | +9.42% |
| us-ig-credit | 4.35% | 6.30% | -1.95% |
| gold | 6.18% | 29.18% | -23.01% |
| commodities | 3.87% | 20.77% | -16.90% |
| kofr-cash | 4.35% | 3.39% | +0.95% |
| money-market | 4.35% | 3.01% | +1.33% |

## Proposed Self-Modifications (logged, not executed)

- **skills/cma_judge/SKILL.md** — Strengthen valuation tilt rule: PE>28 -> +0.10 valuation weight.  
  _Reason: Mean absolute prediction error 13.77% exceeds 6% threshold._
- **agents/asset_class_agent.py** — Add post-judge cap of +200bp above auto-blend for: ['us-treasuries-30y', 'kr-treasuries-10y', 'money-market'].  
  _Reason: Top-3 over-forecast list shows persistent positive bias._