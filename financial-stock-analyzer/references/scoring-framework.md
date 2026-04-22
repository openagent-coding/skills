# Scoring Framework

Score each dimension from **-5** (extremely negative) to **+5** (extremely positive). 0 = neutral.

## Score Calibration

Use these anchors across all dimensions:

| Range | Meaning | Example signals |
|-------|---------|-----------------|
| +4 to +5 | Exceptional / transformative | Revenue >30% YoY growth, breakthrough product, unassailable moat |
| +2 to +3 | Strong positive | Revenue 10-30% growth, successful launches, clear strategy |
| +1 | Mildly positive | Incremental good news, stable improvement |
| 0 | Neutral | No material signal |
| -1 | Mildly negative | Minor setbacks, product delays |
| -2 to -3 | Significantly negative | Major lawsuit, declining revenue, regulatory headwinds |
| -4 to -5 | Crisis / existential | Fraud, bankruptcy risk, industry ban, complete disruption |

## Dimension-Specific Notes

**Financial Health (30% weight)** — Highest weight. Key metrics to compare vs sector median:
- P/E ratio (overvalued if >1.5x sector, undervalued if <0.7x)
- Debt/Equity (flag if >2.0)
- FCF yield (flag if negative 2+ quarters)
- Revenue growth trajectory and gross margin trend

**Long-Term Vision (15%)** — Assess moat on 5 axes: network effects, switching costs, brand power, cost advantages, IP/intangible assets.

**Political & Regulatory (10%)** — Check: revenue concentration by region (flag >30% from at-risk region), supply chain geopolitical dependence, government contract dependence (flag >20% revenue), tariff sensitivity.

**External Factors (15%)** — Check: top 3 raw material price trends, supplier concentration, labor relations, technology disruption timeline (imminent vs 5+ years), climate/weather vulnerability.

## Composite Score

```
Composite = (News × 0.15) + (Financial × 0.30) + (Vision × 0.15) +
            (Political × 0.10) + (Macro × 0.15) + (External × 0.15)
```

## Confidence Adjustment

Reduce confidence one level for each:
- Any dimension with fewer than 2 credible sources
- Dimensions with internally conflicting signals
- Composite driven >50% by a single dimension
- Data older than 30 days in rapidly-changing situations

## Override Rules

Regardless of composite, **downgrade to HOLD** if:
- Financial Health ≤ -3 (fundamental weakness)
- Any dimension is -5 (existential risk)

Regardless of composite, **upgrade to HOLD** if:
- Financial Health ≥ +4 AND the negative signal is from a transient external factor
