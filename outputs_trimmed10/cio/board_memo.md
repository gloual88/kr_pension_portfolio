# Board Memo — Strategic Asset Allocation

_Date: 2026-05-05  |  Pipeline: agentic SAA (offline run)_

## Recommendation

The CIO recommends an allocation produced by the **inverse_te** ensemble across 21 portfolio construction agents. Selection rationale: Regime 'late-cycle' favors 'inverse_te'. Diagnostics: {'simple_average': 0.683, 'inverse_te': 0.681, 'backtest_sharpe': 0.683, 'meta_optimization': 0.2, 'regime_conditional': 0.682, 'composite_score': 0.677, 'trimmed_mean': 0.678}.

- Expected return (3y, nominal): **4.98%**
- Expected volatility: **5.13%**
- Tracking error vs 60/40: **8.41%** (budget 6%)
- Backtest Sharpe: **2.51** (60/40 benchmark: 1.71)
- Backtest max drawdown: **-4.4%** (60/40 benchmark: -13.5%)
- Effective N (Meucci 2009): **9.2**

## Macro Rationale

The macro-agent classifies the environment as **late-cycle** with confidence 0.50 and a 12m recession probability of 20%. Notes: 성장 GDP +3.6%, 수출 +49.2%, 실업 2.7%. 인플레 CPI +2.2%, 유가 $114, USD/KRW 1485. BOK 2.50%, KTB10Y 3.93%, AA-spread 65bp, VIX 17.0.

## Largest Positions

| Asset class | Weight |
|-------------|-------:|
| kofr-cash | 14.26% |
| kr-treasuries-10y | 14.12% |
| money-market | 13.48% |
| us-treasuries-10y | 11.75% |
| us-large-cap | 8.45% |

## Top Contributing PC Agents

| PC Agent | Ensemble weight |
|----------|----------------:|
| inverse-volatility | 16.03% |
| volatility-targeting | 16.03% |
| min-correlation | 9.24% |
| risk-parity | 5.95% |
| mean-downside | 4.64% |
| max-diversification | 3.95% |
| black-litterman | 3.77% |
| equal-weight | 3.64% |

## Key Risks to Monitor

- Stagflationary risk: oil supply shock + sticky core inflation could re-accelerate CPI.
- Concentration in international developed equity (~16% target) — FX risk.
- Long-duration Treasury exposure if inflation surprises above forecast.

## Rebalancing & Drift Triggers

- Frequency: quarterly
- Drift trigger: 5%
- Off-cycle rebalance if any equity-vs-fixed-income drift exceeds 5% absolute.

## IPS Compliance

IPS flags: vol=5.13% outside [6.00%,12.00%]; tracking_error=8.41% exceeds budget 6.00%

## Dissent / Adversarial View

The strategy review's lowest-ranked methods were: mean-downside, adversarial-diversifier, max-dd-constrained. The Adversarial Diversifier in particular receives nonzero weight in the ensemble despite peer rejection because boosting-style ensemble diversification benefits from orthogonal forecasters (Schapire 1990).