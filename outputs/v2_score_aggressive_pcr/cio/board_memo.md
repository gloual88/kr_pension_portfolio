# Board Memo — Strategic Asset Allocation

_Date: 2026-05-08  |  Pipeline: agentic SAA (offline run)_

## Recommendation

The CIO recommends an allocation produced by the **regime_conditional** ensemble across 21 portfolio construction agents. Selection rationale: Regime 'late-cycle' favors 'regime_conditional'. Diagnostics: {'simple_average': 0.705, 'inverse_te': 0.703, 'backtest_sharpe': 0.705, 'meta_optimization': 0.2, 'regime_conditional': 0.705, 'composite_score': 0.701, 'trimmed_mean': 0.704}.

- Expected return (3y, nominal): **5.06%**
- Expected volatility: **6.36%**
- Tracking error vs 60/40: **4.48%** (budget 6%)
- Backtest Sharpe: **2.29** (60/40 benchmark: 2.27)
- Backtest max drawdown: **-6.1%** (60/40 benchmark: -8.1%)
- Effective N (Meucci 2009): **16.1**

## Macro Rationale

The macro-agent classifies the environment as **late-cycle** with confidence 0.52 and a 12m recession probability of 20%. Notes: 성장 GDP +3.6%, 수출 +49.2%, 실업 2.7%. 인플레 CPI +2.6%, 유가 $118, USD/KRW 1451. BOK 2.50%, KTB10Y 3.89%, AA-spread 65bp, VIX 17.4.

## Largest Positions

| Asset class | Weight |
|-------------|-------:|
| kr-credit | 11.06% |
| kofr-cash | 8.84% |
| money-market | 7.29% |
| us-dividend | 6.62% |
| kr-short-bonds | 6.19% |

## Top Contributing PC Agents

| PC Agent | Ensemble weight |
|----------|----------------:|
| max-sharpe | 11.05% |
| black-litterman | 9.94% |
| mean-downside | 8.29% |
| resampled-ef | 7.73% |
| robust-mv | 7.18% |
| inverse-variance | 5.52% |
| tpa | 5.52% |
| market-cap-weight | 5.52% |

## Yield-Curve FI Reallocation

- Curve regime: **bear-parallel**
- FI category total preserved at **34.83%** (equity / cash / real-asset weights unchanged from optimizer output)

| FI ETF | Pre-tilt | Post-tilt | Δ (pp) |
|--------|---------:|----------:|-------:|
| us-treasuries-10y | 6.23% | 5.23% | -1.00 |
| kr-treasuries-10y | 6.13% | 5.14% | -0.99 |
| us-treasuries-30y | 4.05% | 3.39% | -0.65 |
| us-ig-credit | 3.58% | 3.81% | +0.22 |
| kr-credit | 10.41% | 11.06% | +0.65 |
| kr-short-bonds | 4.43% | 6.19% | +1.76 |

## Key Risks to Monitor

- Stagflationary risk: oil supply shock + sticky core inflation could re-accelerate CPI.
- Concentration in international developed equity (~16% target) — FX risk.
- Long-duration Treasury exposure if inflation surprises above forecast.

## Rebalancing & Drift Triggers

- Frequency: quarterly
- Drift trigger: 5%
- Off-cycle rebalance if any equity-vs-fixed-income drift exceeds 5% absolute.

## IPS Compliance

IPS flags: vol=6.36% outside [8.00%,14.00%]

## Dissent / Adversarial View

The strategy review's lowest-ranked methods were: mean-downside, adversarial-diversifier, max-sharpe. The Adversarial Diversifier in particular receives nonzero weight in the ensemble despite peer rejection because boosting-style ensemble diversification benefits from orthogonal forecasters (Schapire 1990).