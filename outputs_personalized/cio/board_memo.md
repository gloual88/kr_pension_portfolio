# Board Memo — Strategic Asset Allocation

_Date: 2026-05-06  |  Pipeline: agentic SAA (offline run)_

## Recommendation

The CIO recommends an allocation produced by the **inverse_te** ensemble across 21 portfolio construction agents. Selection rationale: Regime 'late-cycle' favors 'inverse_te'. Diagnostics: {'simple_average': 0.618, 'inverse_te': 0.617, 'backtest_sharpe': 0.619, 'meta_optimization': 0.2, 'regime_conditional': 0.618, 'composite_score': 0.618, 'trimmed_mean': 0.619}.

- Expected return (3y, nominal): **5.66%**
- Expected volatility: **10.45%**
- Tracking error vs 60/40: **8.66%** (budget 6%)
- Backtest Sharpe: **1.85** (60/40 benchmark: 1.71)
- Backtest max drawdown: **-10.5%** (60/40 benchmark: -13.5%)
- Effective N (Meucci 2009): **12.7**

## Macro Rationale

The macro-agent classifies the environment as **late-cycle** with confidence 0.51 and a 12m recession probability of 20%. Notes: 성장 GDP +3.6%, 수출 +49.2%, 실업 2.7%. 인플레 CPI +2.2%, 유가 $114, USD/KRW 1470. BOK 2.50%, KTB10Y 3.93%, AA-spread 65bp, VIX 18.0.

## Largest Positions

| Asset class | Weight |
|-------------|-------:|
| us-dividend | 9.83% |
| kr-dividend | 9.36% |
| kr-large-cap | 9.18% |
| us-large-cap | 9.16% |
| us-tech | 9.06% |

## Top Contributing PC Agents

| PC Agent | Ensemble weight |
|----------|----------------:|
| inverse-volatility | 7.71% |
| volatility-targeting | 7.71% |
| min-correlation | 7.52% |
| inverse-variance | 6.74% |
| hrp | 6.54% |
| max-diversification | 6.21% |
| equal-weight | 6.01% |
| cvar-min | 6.01% |

## Yield-Curve FI Reallocation

- Curve regime: **bear-parallel**
- FI category total preserved at **16.84%** (equity / cash / real-asset weights unchanged from optimizer output)

| FI ETF | Pre-tilt | Post-tilt | Δ (pp) |
|--------|---------:|----------:|-------:|
| kr-treasuries-10y | 2.98% | 2.50% | -0.48 |
| us-treasuries-10y | 2.61% | 2.18% | -0.42 |
| us-treasuries-30y | 1.64% | 1.37% | -0.27 |
| us-ig-credit | 1.85% | 1.97% | +0.11 |
| kr-credit | 6.00% | 6.37% | +0.37 |
| kr-short-bonds | 1.75% | 2.44% | +0.69 |

## Key Risks to Monitor

- Stagflationary risk: oil supply shock + sticky core inflation could re-accelerate CPI.
- Concentration in international developed equity (~16% target) — FX risk.
- Long-duration Treasury exposure if inflation surprises above forecast.

## Rebalancing & Drift Triggers

- Frequency: quarterly
- Drift trigger: 5%
- Off-cycle rebalance if any equity-vs-fixed-income drift exceeds 5% absolute.

## IPS Compliance

IPS flags: tracking_error=8.66% exceeds budget 6.00%

## Dissent / Adversarial View

The strategy review's lowest-ranked methods were: mean-downside, max-sharpe, adversarial-diversifier. The Adversarial Diversifier in particular receives nonzero weight in the ensemble despite peer rejection because boosting-style ensemble diversification benefits from orthogonal forecasters (Schapire 1990).