# KR 거시경제 레짐 분석 (Self-Driving Pension Portfolio)

**Regime:** late-cycle
**Confidence:** 0.51
**P(recession 12m):** 20%

## 4-Dimension Scores

| Dimension | Score |
|-----------|-------|
| growth | +0.66 |
| inflation | +0.59 |
| monetary | -0.52 |
| financial | -0.27 |

## Notes

성장 GDP +3.6%, 수출 +49.2%, 실업 2.7%. 인플레 CPI +2.2%, 유가 $114, USD/KRW 1470. BOK 2.50%, KTB10Y 3.93%, AA-spread 65bp, VIX 18.0.

## Yield Curve Signal

- State: bear-parallel
- Shape: normal
- Note: KTB 3Y-10Y +32bp, 20d d3Y +18bp, d10Y +21bp, curve d +2bp -> bear-parallel (normal).

## Key Readings

| Indicator | Value | Source |
|-----------|-------|--------|
| kr_gdp_yoy | 3.63 | ECOS 200Y106/1400 @ 2026-01-01 |
| kr_industrial_production_yoy | 1.2 | ECOS 901Y033/A00 @ 2026-03-01 |
| kr_exports_yoy | 49.19 | ECOS 901Y118/T002 @ 2026-03-01 |
| kr_unemployment | 2.7 | ECOS 901Y027/I61BC @ 2026-03-01 |
| kr_cpi_yoy | 2.16 | ECOS 901Y009/0 @ 2026-03-01 (YoY computed) |
| kr_core_cpi_yoy | 2.2 | static fallback |
| kr_brent_oil | 113.89 | FRED DCOILBRENTEU @ 2026-04-27 |
| kr_usd_krw | 1470.5 | ECOS 731Y001/0000001 @ 2026-05-06 |
| kr_base_rate | 2.5 | ECOS 722Y001/0101000 @ 2026-04-01 |
| kr_ktb_10y | 3.932 | ECOS 817Y002/010210000 @ 2026-05-04 |
| kr_ktb_3y | 3.615 | ECOS 817Y002/010200000 @ 2026-05-04 |
| kr_curve_3y_10y | 0.317 | derived: KTB 10Y - KTB 3Y |
| kr_ktb_10y_change_20d | 0.207 | derived: KTB 10Y 20-business-day change |
| kr_ktb_3y_change_20d | 0.183 | derived: KTB 3Y 20-business-day change |
| kr_curve_3y_10y_change_20d | 0.024 | derived: (KTB 10Y - KTB 3Y) 20-business-day change |
| kr_corp_aa_spread_bp | 65.0 | derived: (Corp AA- 3Y - KTB 3Y) × 100 |
| us_fed_funds | 3.64 | FRED DFF @ 2026-05-04 |
| us_vix | 18.0 | static fallback |