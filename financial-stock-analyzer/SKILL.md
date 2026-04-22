---
name: financial-stock-analyzer
description: "Comprehensive financial stock analysis providing buy/sell/hold recommendations based on multi-dimensional research. Gathers and synthesizes: (1) company news from last 6 months, (2) quarterly/annual financial results from last 1 year, (3) company long-term vision and strategy, (4) political and regulatory news, (5) macroeconomic and financial market news, (6) external factors like weather, raw material prices, labor strikes, supply chain, and emerging technology disruptions. Use when: user asks to 'analyze a stock', 'should I buy/sell X', 'financial analysis of X', 'stock recommendation for X', 'evaluate X stock', 'research X company for investment', 'give me a stock report on X', or any request involving investment analysis, stock evaluation, or equity research. Triggers on ticker symbols (AAPL, TSLA, GOOGL, etc.) combined with financial intent."
---

# Financial Stock Analyzer

Multi-dimensional stock analysis producing buy/sell/hold recommendations with evidence.

> **AI-generated research only — not investment advice.** Consult a qualified financial advisor before acting on any recommendation. See `references/disclaimer.md` for full disclaimer.

## Workflow

1. **Parse** — extract ticker(s), time horizon (default: medium-term), risk tolerance (default: moderate), and any user focus areas. Use `AskUserQuestion` if ticker is ambiguous.
2. **Research** — gather data across 6 dimensions using parallel WebSearch calls (see Step 2).
3. **Score** — rate each dimension -5 to +5, compute weighted composite. See `references/scoring-framework.md`.
4. **Report** — generate concise report per `references/report-template.md`. Save to `.claude/reports/stock-analysis-<TICKER>-<YYYYMMDD>.md` (create dir with `mkdir -p` via Bash).
5. **Compare** (if multiple tickers) — run each stock as a parallel `Task` agent, then produce comparison table.

## Step 2: Research (Parallel Data Gathering)

**CRITICAL**: Launch ALL searches in a SINGLE message to maximize parallelism. Use 1-2 WebSearch calls per dimension (6-12 total). After results return, use `WebFetch` on the 2-3 most authoritative URLs (investor relations, SEC filings, major financial outlets) to extract precise numbers.

Craft queries naturally — no quoted strings, adapt terms to the company's sector:

| Dimension | Primary Search | Secondary Search (if needed) |
|-----------|---------------|------------------------------|
| 1. Company News | `<COMPANY> news latest developments <YEAR>` | `<TICKER> analyst upgrade downgrade <YEAR>` |
| 2. Financials | `<TICKER> quarterly earnings revenue EPS <YEAR>` | `<TICKER> PE ratio market cap financial ratios` |
| 3. Vision & Strategy | `<COMPANY> long term strategy competitive moat R&D` | *(skip if primary is rich)* |
| 4. Political & Regulatory | `<COMPANY> regulation tariff export controls <YEAR>` | *(skip if primary is rich)* |
| 5. Macro & Sector | `<SECTOR> outlook <YEAR> <TICKER> analyst price target` | *(skip if primary is rich)* |
| 6. External Factors | `<INDUSTRY> supply chain disruption competition <YEAR>` | `<RAW_MATERIAL> price trend <YEAR>` (if applicable) |

**Cross-validate**: verify key financial numbers (revenue, EPS, margins) appear in at least 2 sources before including in report. Flag unverified data points.

## Step 3: Score & Synthesize

See `references/scoring-framework.md` for rubric, composite formula, confidence adjustments, and override rules.

Quick reference — weights and mapping:

| Dimension | Weight |
|-----------|--------|
| Company News | 15% |
| Financial Health | 30% |
| Long-Term Vision | 15% |
| Political/Regulatory | 10% |
| Macro Environment | 15% |
| External Factors | 15% |

| Composite | Recommendation |
|-----------|---------------|
| +3.0 to +5.0 | STRONG BUY |
| +1.5 to +2.9 | BUY |
| +0.5 to +1.4 | LEAN BUY |
| -0.4 to +0.4 | HOLD |
| -1.4 to -0.5 | LEAN SELL |
| -2.9 to -1.5 | SELL |
| -5.0 to -3.0 | STRONG SELL |

## Step 5: Multi-Stock (if applicable)

Launch a separate `Task` agent (subagent_type=`general-purpose`) per ticker for parallel analysis. After all complete, produce a side-by-side comparison table ranking by composite score with portfolio allocation suggestion based on risk tolerance.

## Error Handling

| Scenario | Action |
|----------|--------|
| No search results for a dimension | Note gap; redistribute weight; lower confidence |
| Conflicting data | Present both sides; weight toward more authoritative/recent source |
| Private or micro-cap company | Warn user; focus on available dimensions |
| Crypto/forex (not equities) | Inform user this skill targets equities; offer best-effort with caveats |

## Arguments

- `/financial-stock-analyzer AAPL` — single stock
- `/financial-stock-analyzer TSLA RIVN` — multi-stock comparison
- `/financial-stock-analyzer MSFT --horizon=long-term --risk=aggressive` — with parameters
