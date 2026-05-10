# Board Memo — Strategic Asset Allocation

_Date: 2026-05-10  |  Pipeline: agentic SAA (offline run)_

## Recommendation

The CIO recommends an allocation produced by the **inverse_te** ensemble across 21 portfolio construction agents. Selection rationale: Regime 'late-cycle' favors 'inverse_te'. Diagnostics: {'simple_average': 0.77, 'inverse_te': 0.769, 'backtest_sharpe': 0.77, 'meta_optimization': 0.2, 'regime_conditional': 0.77, 'composite_score': 0.769, 'trimmed_mean': 0.77}.

- Expected return (3y, nominal): **5.43%**
- Expected volatility: **9.07%**
- Tracking error vs 60/40: **8.65%** (budget 6%)
- Backtest Sharpe: **2.26** (60/40 benchmark: 1.81)
- Backtest max drawdown: **-9.1%** (60/40 benchmark: -13.5%)
- Effective N (Meucci 2009): **16.0**

## Macro Rationale

The macro-agent classifies the environment as **late-cycle** with confidence 0.52 and a 12m recession probability of 20%. Notes: 성장 GDP +3.6%, 수출 +49.2%, 실업 2.7%. 인플레 CPI +2.6%, 유가 $118, USD/KRW 1451. BOK 2.50%, KTB10Y 3.91%, AA-spread 65bp, VIX 17.1.

## Largest Positions

| Asset class | Weight |
|-------------|-------:|
| gold | 7.75% |
| us-dividend | 7.40% |
| kr-credit | 7.32% |
| commodities | 7.25% |
| kr-dividend | 6.92% |

## Top Contributing PC Agents

| PC Agent | Ensemble weight |
|----------|----------------:|
| inverse-volatility | 9.47% |
| volatility-targeting | 9.47% |
| min-correlation | 8.54% |
| max-diversification | 7.61% |
| inverse-variance | 6.68% |
| hrp | 6.51% |
| equal-weight | 5.83% |
| cvar-min | 5.83% |

## Yield-Curve FI Reallocation

- Curve regime: **bear-parallel**
- FI category total preserved at **25.56%** (equity / cash / real-asset weights unchanged from optimizer output)

| FI ETF | Pre-tilt | Post-tilt | Δ (pp) |
|--------|---------:|----------:|-------:|
| kr-treasuries-10y | 4.73% | 3.95% | -0.79 |
| us-treasuries-10y | 4.17% | 3.48% | -0.69 |
| us-treasuries-30y | 2.85% | 2.38% | -0.47 |
| us-ig-credit | 3.35% | 3.54% | +0.19 |
| kr-credit | 6.93% | 7.32% | +0.39 |
| kr-short-bonds | 3.52% | 4.89% | +1.37 |

## Key Risks to Monitor

- Stagflationary risk: oil supply shock + sticky core inflation could re-accelerate CPI.
- Concentration in international developed equity (~16% target) — FX risk.
- Long-duration Treasury exposure if inflation surprises above forecast.

## Rebalancing & Drift Triggers

- Frequency: quarterly
- Drift trigger: 5%
- Off-cycle rebalance if any equity-vs-fixed-income drift exceeds 5% absolute.

## IPS Compliance

IPS flags: tracking_error=8.65% exceeds budget 6.00%

## Dissent / Adversarial View

The strategy review's lowest-ranked methods were: resampled-ef, max-sharpe, adversarial-diversifier. The Adversarial Diversifier in particular receives nonzero weight in the ensemble despite peer rejection because boosting-style ensemble diversification benefits from orthogonal forecasters (Schapire 1990).