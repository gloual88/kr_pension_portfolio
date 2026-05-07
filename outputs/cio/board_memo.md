# Board Memo — Strategic Asset Allocation

_Date: 2026-05-06  |  Pipeline: agentic SAA (offline run)_

## Recommendation

The CIO recommends an allocation produced by the **inverse_te** ensemble across 21 portfolio construction agents. Selection rationale: Regime 'late-cycle' favors 'inverse_te'. Diagnostics: {'simple_average': 0.662, 'inverse_te': 0.664, 'backtest_sharpe': 0.662, 'meta_optimization': 0.2, 'regime_conditional': 0.662, 'composite_score': 0.658, 'trimmed_mean': 0.657}.

- Expected return (3y, nominal): **4.93%**
- Expected volatility: **4.71%**
- Tracking error vs 60/40: **8.80%** (budget 6%)
- Backtest Sharpe: **2.29** (60/40 benchmark: 1.71)
- Backtest max drawdown: **-4.3%** (60/40 benchmark: -13.5%)
- Effective N (Meucci 2009): **12.9**

## Macro Rationale

The macro-agent classifies the environment as **late-cycle** with confidence 0.51 and a 12m recession probability of 20%. Notes: 성장 GDP +3.6%, 수출 +49.2%, 실업 2.7%. 인플레 CPI +2.2%, 유가 $114, USD/KRW 1470. BOK 2.50%, KTB10Y 3.93%, AA-spread 65bp, VIX 18.3.

## Largest Positions

| Asset class | Weight |
|-------------|-------:|
| kofr-cash | 13.80% |
| kr-credit | 13.14% |
| money-market | 11.27% |
| kr-short-bonds | 7.15% |
| kr-treasuries-10y | 6.49% |

## Top Contributing PC Agents

| PC Agent | Ensemble weight |
|----------|----------------:|
| inverse-volatility | 9.81% |
| volatility-targeting | 9.81% |
| min-correlation | 8.93% |
| max-diversification | 5.96% |
| risk-parity | 5.92% |
| mean-downside | 5.19% |
| robust-mv | 4.69% |
| resampled-ef | 4.62% |

## Yield-Curve FI Reallocation

- Curve regime: **bear-parallel**
- FI category total preserved at **40.27%** (equity / cash / real-asset weights unchanged from optimizer output)

| FI ETF | Pre-tilt | Post-tilt | Δ (pp) |
|--------|---------:|----------:|-------:|
| kr-treasuries-10y | 7.75% | 6.49% | -1.26 |
| us-treasuries-10y | 7.26% | 6.08% | -1.18 |
| us-treasuries-30y | 3.75% | 3.15% | -0.61 |
| us-ig-credit | 4.01% | 4.25% | +0.25 |
| kr-credit | 12.38% | 13.14% | +0.76 |
| kr-short-bonds | 5.12% | 7.15% | +2.03 |

## Key Risks to Monitor

- Stagflationary risk: oil supply shock + sticky core inflation could re-accelerate CPI.
- Concentration in international developed equity (~16% target) — FX risk.
- Long-duration Treasury exposure if inflation surprises above forecast.

## Rebalancing & Drift Triggers

- Frequency: quarterly
- Drift trigger: 5%
- Off-cycle rebalance if any equity-vs-fixed-income drift exceeds 5% absolute.

## IPS Compliance

IPS flags: vol=4.71% outside [6.00%,12.00%]; tracking_error=8.80% exceeds budget 6.00%

## Dissent / Adversarial View

The strategy review's lowest-ranked methods were: market-cap-weight, max-sharpe, adversarial-diversifier. The Adversarial Diversifier in particular receives nonzero weight in the ensemble despite peer rejection because boosting-style ensemble diversification benefits from orthogonal forecasters (Schapire 1990).