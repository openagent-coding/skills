# Financial Stock Analyzer

Multi-dimensional stock analysis producing buy/sell/hold recommendations with evidence-based scoring.

> **AI-generated research only -- not investment advice.** Consult a qualified financial advisor before acting on any recommendation.

## Overview

Gathers and synthesizes data across six research dimensions using parallel web searches, scores each dimension on a -5 to +5 scale, computes a weighted composite, and maps it to a recommendation from STRONG BUY to STRONG SELL.

## Research Dimensions

| Dimension | Weight | What It Covers |
|-----------|--------|----------------|
| Company News | 15% | Latest developments, analyst upgrades/downgrades |
| Financial Health | 30% | Quarterly/annual earnings, revenue, EPS, ratios |
| Long-Term Vision | 15% | Strategy, competitive moat, R&D |
| Political/Regulatory | 10% | Regulation, tariffs, export controls |
| Macro Environment | 15% | Sector outlook, analyst price targets |
| External Factors | 15% | Supply chain, raw materials, competition, disruptions |

## Recommendation Scale

| Composite Score | Recommendation |
|-----------------|---------------|
| +3.0 to +5.0 | STRONG BUY |
| +1.5 to +2.9 | BUY |
| +0.5 to +1.4 | LEAN BUY |
| -0.4 to +0.4 | HOLD |
| -1.4 to -0.5 | LEAN SELL |
| -2.9 to -1.5 | SELL |
| -5.0 to -3.0 | STRONG SELL |

## Usage

```
/financial-stock-analyzer AAPL                              # Single stock
/financial-stock-analyzer TSLA RIVN                         # Multi-stock comparison
/financial-stock-analyzer MSFT --horizon=long-term --risk=aggressive  # With parameters
```

Multi-stock requests launch parallel analysis agents per ticker and produce a side-by-side comparison table.

## Output

Reports are saved to `.claude/reports/stock-analysis-<TICKER>-<YYYYMMDD>.md`.

## References

- [Scoring framework](references/scoring-framework.md)
- [Report template](references/report-template.md)
- [Disclaimer](references/disclaimer.md)