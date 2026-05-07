# Macro Regime Skill

Classifies the current macro environment into one of four regimes:
**expansion**, **late-cycle**, **recession**, **recovery**.

The skill scores four dimensions on a -1 to +1 scale:
- `growth`        : real GDP, payrolls, ISM
- `inflation`     : CPI/core CPI, breakevens, oil
- `monetary`      : policy stance (cuts/hikes, rate level vs neutral)
- `financial`     : credit spreads, equity vol, dollar, term structure

A weighted aggregate maps to a regime label and a confidence level in [0, 1].

## Regime Decision Rules

| growth | inflation | mon. policy | fin. cond. | regime      |
|--------|-----------|-------------|-----------|-------------|
|   +    |    -      |   -         |    +      | expansion   |
|   +    |    +      |   +         |    -      | late-cycle  |
|   -    |   +/-     |   --        |    -      | recession   |
|   +    |    -      |   --        |    +      | recovery    |

Confidence = `1 - mean(|score - 1|)/2` for the dominant dimensions.

## Inputs

- `data.csv` macro/market readings (GDP YoY, CPI YoY, core CPI YoY,
  unemployment, payrolls 3m avg, ISM, fed funds, 10Y, 2s10s, HY OAS, VIX,
  USD index, oil).

## Outputs

- `macro-view.json` with regime, confidence, dimension scores, and notes.
