# Session Metrics Tracker

Silent background telemetry that records context length, LLM call count, and human interrupt count on every tool call, producing matplotlib-ready CSV reports with companion markdown summaries.

## Overview

A PostToolUse hook appends a JSON line per tool call to a session log. On demand, it generates reports with cumulative metrics, per-tool breakdowns, interrupt timelines, and context growth analysis.

## Metrics Tracked

| Metric | Description |
|--------|-------------|
| Context length (tokens) | Estimated cumulative token consumption from tool I/O |
| LLM calls | Autonomous agent actions (all tool calls except AskUserQuestion) |
| Human interrupts | Clarification pauses (AskUserQuestion invocations) |
| Autonomy score | `llm_calls / total_events * 100` |
| Context utilization | Percentage of model context limit consumed |
| Per-tool breakdown | Frequency and avg output size by tool name |

## Setup

Add the PostToolUse hook to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "type": "command",
        "command": "python3 .claude/skills/session-metrics-tracker/scripts/record_event.py"
      }
    ]
  }
}
```

## Usage

```
/session-metrics-tracker                   # Generate CSV + markdown report
/session-metrics-tracker --plot            # Also generate a PNG plot
/session-metrics-tracker --reset           # Archive current session, start fresh
/session-metrics-tracker --report-dir=/tmp/metrics  # Custom output directory
```

## Output

Reports are written to `.claude/reports/`:

| File | Contents |
|------|----------|
| `session-report-*.csv` | Matplotlib-ready tabular data (one row per event) |
| `session-report-*.md` | Summary table, tool breakdown, interrupt timeline, context growth |
| `session-plot-*.png` | Three-subplot chart (context growth, call counts, per-event tokens) |

## Architecture

- **No state file** -- each event is a self-contained JSON line in `session-metrics-current.jsonl`
- **No external dependencies** -- Python standard library only
- **No stdout** -- hook produces no visible output during conversations
