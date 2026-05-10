# KR 거시경제 레짐 분석 (Self-Driving Pension Portfolio)

**Regime:** late-cycle
**Confidence:** 0.52
**P(recession 12m):** 20%

## 4-Dimension Scores

| Dimension | Score |
|-----------|-------|
| growth | +0.66 |
| inflation | +0.69 |
| monetary | -0.50 |
| financial | -0.24 |

## Notes

성장 GDP +3.6%, 수출 +49.2%, 실업 2.7%. 인플레 CPI +2.6%, 유가 $118, USD/KRW 1451. BOK 2.50%, KTB10Y 3.91%, AA-spread 65bp, VIX 17.1.

## Yield Curve Signal

- State: bear-parallel
- Shape: normal
- Note: KTB 3Y-10Y +34bp, 20d d3Y +21bp, d10Y +22bp, curve d +1bp -> bear-parallel (normal).

## Key Readings

| Indicator | Value | Source |
|-----------|-------|--------|
| kr_gdp_yoy | 3.63 | ECOS 200Y106/1400 @ 2026-01-01 |
| kr_industrial_production_yoy | 1.2 | ECOS 901Y033/A00 @ 2026-03-01 |
| kr_exports_yoy | 49.19 | ECOS 901Y118/T002 @ 2026-03-01 |
| kr_unemployment | 2.7 | ECOS 901Y027/I61BC @ 2026-03-01 |
| kr_cpi_yoy | 2.57 | ECOS 901Y009/0 @ 2026-04-01 (YoY computed) |
| kr_core_cpi_yoy | 2.2 | static fallback |
| kr_brent_oil | 118.26 | FRED DCOILBRENTEU @ 2026-05-01 |
| kr_usd_krw | 1450.8 | ECOS 731Y001/0000001 @ 2026-05-08 |
| kr_base_rate | 2.5 | ECOS 722Y001/0101000 @ 2026-04-01 |
| kr_ktb_10y | 3.909 | ECOS 817Y002/010210000 @ 2026-05-08 |
| kr_ktb_3y | 3.569 | ECOS 817Y002/010200000 @ 2026-05-08 |
| kr_curve_3y_10y | 0.34 | derived: KTB 10Y - KTB 3Y |
| kr_ktb_10y_change_20d | 0.223 | derived: KTB 10Y 20-business-day change |
| kr_ktb_3y_change_20d | 0.209 | derived: KTB 3Y 20-business-day change |
| kr_curve_3y_10y_change_20d | 0.014 | derived: (KTB 10Y - KTB 3Y) 20-business-day change |
| kr_corp_aa_spread_bp | 65.0 | derived: (Corp AA- 3Y - KTB 3Y) × 100 |
| us_fed_funds | 3.63 | FRED DFF @ 2026-05-07 |
| us_vix | 17.08 | FRED VIXCLS @ 2026-05-07 |