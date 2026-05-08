# Board Memo — Strategic Asset Allocation

_Date: 2026-05-08  |  Pipeline: agentic SAA (offline run)_

## Recommendation

The CIO recommends an allocation produced by the **inverse_te** ensemble across 21 portfolio construction agents. Selection rationale: Regime 'late-cycle' favors 'inverse_te'. Diagnostics: {'simple_average': 0.661, 'inverse_te': 0.663, 'backtest_sharpe': 0.661, 'meta_optimization': 0.2, 'regime_conditional': 0.661, 'composite_score': 0.657, 'trimmed_mean': 0.656}.

- Expected return (3y, nominal): **4.26%**
- Expected volatility: **4.76%**
- Tracking error vs 60/40: **8.81%** (budget 6%)
- Backtest Sharpe: **2.34** (60/40 benchmark: 1.81)
- Backtest max drawdown: **-4.4%** (60/40 benchmark: -13.5%)
- Effective N (Meucci 2009): **12.9**

## Macro Rationale

The macro-agent classifies the environment as **late-cycle** with confidence 0.51 and a 12m recession probability of 20%. Notes: 성장 GDP +3.6%, 수출 +49.2%, 실업 2.7%. 인플레 CPI +2.6%, 유가 $95, USD/KRW 1451. BOK 2.50%, KTB10Y 3.89%, AA-spread 65bp, VIX 17.4.

## Largest Positions

| Asset class | Weight |
|-------------|-------:|
| kofr-cash | 13.76% |
| kr-credit | 13.11% |
| money-market | 11.25% |
| kr-short-bonds | 6.98% |
| kr-treasuries-10y | 6.38% |

## Top Contributing PC Agents

| PC Agent | Ensemble weight |
|----------|----------------:|
| inverse-volatility | 9.51% |
| volatility-targeting | 9.51% |
| min-correlation | 8.60% |
| max-diversification | 5.84% |
| risk-parity | 5.82% |
| robust-mv | 5.49% |
| inverse-variance | 4.74% |
| resampled-ef | 4.70% |

## Yield-Curve FI Reallocation

- Curve regime: **bear-parallel**
- FI category total preserved at **39.89%** (equity / cash / real-asset weights unchanged from optimizer output)

| FI ETF | Pre-tilt | Post-tilt | Δ (pp) |
|--------|---------:|----------:|-------:|
| kr-treasuries-10y | 7.60% | 6.38% | -1.23 |
| us-treasuries-10y | 7.33% | 6.14% | -1.18 |
| us-treasuries-30y | 3.66% | 3.07% | -0.59 |
| us-ig-credit | 3.96% | 4.20% | +0.25 |
| kr-credit | 12.34% | 13.11% | +0.77 |
| kr-short-bonds | 5.00% | 6.98% | +1.99 |

## Key Risks to Monitor

- Stagflationary risk: oil supply shock + sticky core inflation could re-accelerate CPI.
- Concentration in international developed equity (~16% target) — FX risk.
- Long-duration Treasury exposure if inflation surprises above forecast.

## Rebalancing & Drift Triggers

- Frequency: quarterly
- Drift trigger: 5%
- Off-cycle rebalance if any equity-vs-fixed-income drift exceeds 5% absolute.

## IPS Compliance

IPS flags: vol=4.76% outside [6.00%,12.00%]; tracking_error=8.81% exceeds budget 6.00%

## Dissent / Adversarial View

The strategy review's lowest-ranked methods were: resampled-ef, adversarial-diversifier, max-sharpe. The Adversarial Diversifier in particular receives nonzero weight in the ensemble despite peer rejection because boosting-style ensemble diversification benefits from orthogonal forecasters (Schapire 1990).