# Board Memo — Strategic Asset Allocation

_Date: 2026-05-10  |  Pipeline: agentic SAA (offline run)_

## Recommendation

The CIO recommends an allocation produced by the **inverse_te** ensemble across 21 portfolio construction agents. Selection rationale: Regime 'late-cycle' favors 'inverse_te'. Diagnostics: {'simple_average': 0.786, 'inverse_te': 0.785, 'backtest_sharpe': 0.785, 'meta_optimization': 0.2, 'regime_conditional': 0.785, 'composite_score': 0.785, 'trimmed_mean': 0.786}.

- Expected return (3y, nominal): **5.52%**
- Expected volatility: **8.87%**
- Tracking error vs 60/40: **8.09%** (budget 6%)
- Backtest Sharpe: **2.44** (60/40 benchmark: 1.81)
- Backtest max drawdown: **-7.8%** (60/40 benchmark: -13.5%)
- Effective N (Meucci 2009): **8.3**

## Macro Rationale

The macro-agent classifies the environment as **late-cycle** with confidence 0.52 and a 12m recession probability of 20%. Notes: 성장 GDP +3.6%, 수출 +49.2%, 실업 2.7%. 인플레 CPI +2.6%, 유가 $118, USD/KRW 1451. BOK 2.50%, KTB10Y 3.91%, AA-spread 65bp, VIX 17.1.

## Largest Positions

| Asset class | Weight |
|-------------|-------:|
| gold | 15.00% |
| kr-dividend | 14.03% |
| us-large-cap | 13.86% |
| kr-large-cap | 13.75% |
| us-tech | 13.36% |

## Top Contributing PC Agents

| PC Agent | Ensemble weight |
|----------|----------------:|
| inverse-volatility | 10.68% |
| volatility-targeting | 10.68% |
| tpa | 7.41% |
| max-diversification | 7.23% |
| inverse-variance | 6.20% |
| hrp | 6.07% |
| black-litterman | 5.91% |
| equal-weight | 5.73% |

## Yield-Curve FI Reallocation

- Curve regime: **bear-parallel**
- FI category total preserved at **25.39%** (equity / cash / real-asset weights unchanged from optimizer output)

| FI ETF | Pre-tilt | Post-tilt | Δ (pp) |
|--------|---------:|----------:|-------:|
| kr-treasuries-10y | 9.71% | 9.04% | -0.67 |
| us-treasuries-10y | 8.60% | 8.01% | -0.60 |
| us-ig-credit | 7.08% | 8.34% | +1.27 |

## Key Risks to Monitor

- Stagflationary risk: oil supply shock + sticky core inflation could re-accelerate CPI.
- Concentration in international developed equity (~16% target) — FX risk.
- Long-duration Treasury exposure if inflation surprises above forecast.

## Rebalancing & Drift Triggers

- Frequency: quarterly
- Drift trigger: 5%
- Off-cycle rebalance if any equity-vs-fixed-income drift exceeds 5% absolute.

## IPS Compliance

IPS flags: tracking_error=8.09% exceeds budget 6.00%

## Dissent / Adversarial View

The strategy review's lowest-ranked methods were: resampled-ef, max-sharpe, adversarial-diversifier. The Adversarial Diversifier in particular receives nonzero weight in the ensemble despite peer rejection because boosting-style ensemble diversification benefits from orthogonal forecasters (Schapire 1990).