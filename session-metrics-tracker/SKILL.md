---
name: session-metrics-tracker
description: "Background session telemetry that silently records context length, LLM call count, and human interrupt count on every tool call. Generates matplotlib-ready CSV reports with companion markdown summaries. Runs via PostToolUse hook without interrupting the main process. Use /session-metrics-tracker to generate or plot the current session report. Supports --report-dir to override the default output directory ($PROJECT_ROOT/.claude/reports/)."
---

# Session Metrics Tracker

Silent background telemetry that records per-event metrics on every tool call and produces matplotlib-ready CSV reports with rich markdown summaries on demand.

## What It Tracks

| Metric | Source | Description |
|--------|--------|-------------|
| Context length (tokens) | Tool args + output sizes | Estimated cumulative token consumption from tool I/O |
| LLM calls | Every tool invocation except `AskUserQuestion` | Autonomous agent actions |
| Human interrupts | `AskUserQuestion` invocations | Clarifications / missing-instruction pauses |
| Autonomy score | `llm_calls / total_events * 100` | Percentage of events that were autonomous |
| Context utilization | `cumulative_tokens / 200K * 100` | How close to the model context limit |
| Per-tool breakdown | Tool name frequency + output sizes | Which tools consume the most context |

> **Known limitation**: Context estimates cover tool I/O only (args + output).
> The assistant's own responses and system prompts also consume context but
> are not available to PostToolUse hooks. Actual usage is typically 1.5–2.5x
> the reported value.

## Architecture

### Background Recording (automatic — no state file)

A PostToolUse hook calls `scripts/record_event.py` after every tool call. The script:

1. Reads `CLAUDE_TOOL_NAME`, `CLAUDE_TOOL_ARGS`, `CLAUDE_TOOL_OUTPUT` from the environment
2. Classifies the event as `llm_call` or `human_interrupt`
3. Estimates token consumption:
   - **Tool args** → always uses the structured-data ratio (2.5 chars/token) since args are always JSON
   - **Tool output** → detects content type from a 512-char prefix using regex word-boundary checks, then applies the appropriate ratio to the full length
4. Appends a single JSON line to the session log
5. Produces **no stdout** so it never interrupts the conversation

There is **no state file**. Each event is a self-contained record. All cumulative
counters and derived metrics are computed at report-generation time. This
eliminates the read-modify-write race condition that a state file would create
if hooks ever overlapped, and reduces the hot path to a single atomic file append.

Data file:
- **Log**: `.claude/reports/session-metrics-current.jsonl`

### Report Generation (on demand)

Run when the user invokes `/session-metrics-tracker` or asks for session metrics.

#### Step 1: Parse arguments

Extract flags from `$ARGUMENTS`:
- `--report-dir=<path>` — override output directory (default: `.claude/reports/`)
- `--format=csv|json|markdown` — primary output format (default: `csv`)
- `--context-limit=N` — model context window in tokens (default: `200000`)
- `--reset` — archive current session and start fresh
- `--plot` — also generate a PNG plot (requires matplotlib)

If no flags, generate a CSV report + companion markdown summary to the default directory.

#### Step 2: Generate report

```bash
python3 .claude/skills/session-metrics-tracker/scripts/generate_report.py \
  --report-dir .claude/reports/
```

This reads `session-metrics-current.jsonl`, computes all cumulative and derived
metrics, and writes:

- `session-report-YYYYMMDD-HHMMSS.csv` — matplotlib-ready tabular data
- `session-report-YYYYMMDD-HHMMSS.md` — human-readable companion report

The markdown report includes:
- **Summary table** — totals, autonomy score, context utilization
- **Tool usage breakdown** — sorted by frequency with avg output tokens
- **Interrupt timeline** — when each clarification happened and what preceded it
- **Context growth segments** — token accumulation rate between interrupts
- **Top token consumers** — the events that added the most to context

#### Step 3: Display summary

Show the user the summary JSON returned by the script. It includes:
- Total events, LLM calls, human interrupts, autonomy score
- Estimated context tokens, context utilization percentage
- Average tokens per event, session duration
- Per-tool breakdown, interrupt details
- Paths to the generated report files

#### Step 4: Plot (if --plot)

```bash
python3 .claude/skills/session-metrics-tracker/scripts/plot_session.py \
  --report-dir .claude/reports/ \
  --output .claude/reports/session-plot-YYYYMMDD-HHMMSS.png
```

The plot has three subplots:
1. **Context Length Growth** — line plot with interrupt markers
2. **LLM Calls vs Human Interrupts** — cumulative counts with autonomy annotation
3. **Per-Event Token Consumption** — bar chart colored by event type

#### Step 5: Reset (if --reset)

```bash
python3 .claude/skills/session-metrics-tracker/scripts/generate_report.py \
  --report-dir .claude/reports/ --reset
```

This archives the current JSONL log with a timestamp suffix and starts a fresh session.

## Report CSV Schema

The CSV has these columns, one row per tool call event:

```csv
call_number,timestamp,elapsed_seconds,event_type,tool_name,args_tokens,output_tokens,event_tokens,cumulative_context_tokens,cumulative_llm_calls,cumulative_interrupts
```

## Plotting with matplotlib

The plot script accepts **both CSV and JSONL** as input — no intermediate step required.

```bash
# Plot from latest CSV report
python3 .claude/skills/session-metrics-tracker/scripts/plot_session.py \
  --report-dir .claude/reports/

# Plot directly from raw JSONL log (no report generation needed)
python3 .claude/skills/session-metrics-tracker/scripts/plot_session.py \
  .claude/reports/session-metrics-current.jsonl

# Use elapsed time as x-axis instead of event number
python3 .claude/skills/session-metrics-tracker/scripts/plot_session.py \
  --report-dir .claude/reports/ --x-axis time

# Save to file
python3 .claude/skills/session-metrics-tracker/scripts/plot_session.py \
  --report-dir .claude/reports/ --output plot.png
```

## Hook Integration

The PostToolUse hook in `.claude/settings.json` must include:

```json
{
  "type": "command",
  "command": "python3 .claude/skills/session-metrics-tracker/scripts/record_event.py"
}
```

This hook produces no visible output and does not affect the main conversation flow.

## Arguments

- `/session-metrics-tracker` — generate CSV + markdown report to default directory
- `/session-metrics-tracker --report-dir=/tmp/metrics` — generate to custom directory
- `/session-metrics-tracker --format=json` — generate JSON + markdown report
- `/session-metrics-tracker --format=markdown` — generate markdown report only
- `/session-metrics-tracker --plot` — generate CSV + markdown + PNG plot
- `/session-metrics-tracker --reset` — archive current session, start fresh
- `/session-metrics-tracker --context-limit=1000000` — use 1M token context limit
- `/session-metrics-tracker --report-dir=/tmp/metrics --plot --reset` — combine flags
