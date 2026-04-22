#!/usr/bin/env python3
"""
Generate session metrics reports from raw JSONL event data.

Supports three output formats:
  csv       — matplotlib-ready tabular data (default)
  json      — machine-readable structured data
  markdown  — human-readable report with tables, breakdowns, and analysis

A companion markdown summary is always generated alongside csv/json output
so users get both a plottable file and a readable report.

Usage:
    python generate_report.py                                # CSV + markdown
    python generate_report.py --report-dir /tmp/metrics      # custom directory
    python generate_report.py --format json                  # JSON + markdown
    python generate_report.py --format markdown              # markdown only
    python generate_report.py --reset                        # archive + fresh start
    python generate_report.py --input path/to/file.jsonl     # specific log file
    python generate_report.py --context-limit 200000         # custom model limit
"""

import argparse
import csv
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

_DEFAULT_CONTEXT_LIMIT = 200_000


# ── Data loading & enrichment ────────────────────────────────────────────────

def _load_events(path: str) -> list[dict]:
    """Read raw JSONL events, skipping malformed lines."""
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def _enrich_events(raw_events: list[dict]) -> list[dict]:
    """Add derived fields: call_number, elapsed_seconds, cumulative counters.

    Works with both old-format events (that already have cumulative fields)
    and new-format events (raw only). Recomputes everything from scratch
    so the output is always consistent.
    """
    if not raw_events:
        return []

    start_ts = datetime.fromisoformat(raw_events[0]["ts"])
    cum_ctx = 0
    cum_llm = 0
    cum_int = 0

    enriched = []
    for i, e in enumerate(raw_events, 1):
        evt_ts = datetime.fromisoformat(e["ts"])
        elapsed = (evt_ts - start_ts).total_seconds()

        args_tok = e.get("args_tokens", 0)
        out_tok = e.get("output_tokens", 0)
        event_tokens = args_tok + out_tok
        cum_ctx += event_tokens

        evt_type = e.get("event_type", "llm_call")
        if evt_type == "human_interrupt":
            cum_int += 1
        else:
            cum_llm += 1

        enriched.append({
            "call_number": i,
            "ts": e["ts"],
            "elapsed_seconds": round(elapsed, 1),
            "event_type": evt_type,
            "tool_name": e.get("tool_name", "unknown"),
            "args_tokens": args_tok,
            "output_tokens": out_tok,
            "event_tokens": event_tokens,
            "cumulative_context_tokens": cum_ctx,
            "cumulative_llm_calls": cum_llm,
            "cumulative_interrupts": cum_int,
        })

    return enriched


# ── Summary computation ──────────────────────────────────────────────────────

def _compute_summary(events: list[dict], report_path: str,
                     md_path: str | None, context_limit: int) -> dict:
    """Compute rich session statistics from enriched events."""
    if not events:
        return {"error": "no events"}

    first, last = events[0], events[-1]
    total = len(events)
    llm = last["cumulative_llm_calls"]
    interrupts = last["cumulative_interrupts"]
    ctx_tokens = last["cumulative_context_tokens"]

    autonomy = round(llm / total * 100, 1) if total else 0.0
    ctx_pct = round(ctx_tokens / context_limit * 100, 1) if context_limit else 0.0
    avg_tokens = round(ctx_tokens / total) if total else 0

    # Per-tool breakdown
    tool_counts: Counter[str] = Counter()
    tool_output_sum: dict[str, int] = {}
    for e in events:
        tn = e["tool_name"]
        tool_counts[tn] += 1
        tool_output_sum[tn] = tool_output_sum.get(tn, 0) + e["output_tokens"]

    tool_breakdown = []
    for tn, count in tool_counts.most_common():
        tool_breakdown.append({
            "tool": tn,
            "count": count,
            "percentage": round(count / total * 100, 1),
            "avg_output_tokens": round(tool_output_sum[tn] / count),
        })

    # Interrupt details
    interrupt_events = [
        {
            "at_event": e["call_number"],
            "context_tokens": e["cumulative_context_tokens"],
            "preceding_tool": events[e["call_number"] - 2]["tool_name"]
                              if e["call_number"] > 1 else "—",
        }
        for e in events if e["event_type"] == "human_interrupt"
    ]

    result = {
        "report_file": report_path,
        "total_events": total,
        "llm_calls": llm,
        "human_interrupts": interrupts,
        "autonomy_score_pct": autonomy,
        "estimated_context_tokens": ctx_tokens,
        "context_limit": context_limit,
        "context_utilization_pct": ctx_pct,
        "avg_tokens_per_event": avg_tokens,
        "session_start": first["ts"],
        "session_end": last["ts"],
        "session_duration_seconds": last["elapsed_seconds"],
        "tool_breakdown": tool_breakdown,
        "interrupts": interrupt_events,
    }
    if md_path:
        result["markdown_file"] = md_path
    return result


# ── CSV output ───────────────────────────────────────────────────────────────

_CSV_FIELDS = [
    "call_number", "timestamp", "elapsed_seconds", "event_type", "tool_name",
    "args_tokens", "output_tokens", "event_tokens",
    "cumulative_context_tokens", "cumulative_llm_calls", "cumulative_interrupts",
]


def _write_csv(events: list[dict], output_path: str) -> None:
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for e in events:
            writer.writerow({
                "call_number": e["call_number"],
                "timestamp": e["ts"],
                "elapsed_seconds": e["elapsed_seconds"],
                "event_type": e["event_type"],
                "tool_name": e["tool_name"],
                "args_tokens": e["args_tokens"],
                "output_tokens": e["output_tokens"],
                "event_tokens": e["event_tokens"],
                "cumulative_context_tokens": e["cumulative_context_tokens"],
                "cumulative_llm_calls": e["cumulative_llm_calls"],
                "cumulative_interrupts": e["cumulative_interrupts"],
            })


# ── JSON output ──────────────────────────────────────────────────────────────

def _write_json(events: list[dict], summary: dict, output_path: str) -> None:
    with open(output_path, "w") as f:
        json.dump({
            "summary": summary,
            "events": events,
            "generated_at": datetime.now().isoformat(),
        }, f, indent=2)


# ── Markdown output ──────────────────────────────────────────────────────────

def _format_duration(seconds: float) -> str:
    s = int(seconds)
    if s >= 3600:
        return f"{s // 3600}h {(s % 3600) // 60}m {s % 60}s"
    if s >= 60:
        return f"{s // 60}m {s % 60}s"
    return f"{seconds:.1f}s"


def _write_markdown(events: list[dict], summary: dict, output_path: str) -> None:
    total = summary["total_events"]
    dur_str = _format_duration(summary["session_duration_seconds"])
    start_short = summary["session_start"][:19].replace("T", " ")
    end_short = summary["session_end"][11:19]

    lines = [
        "# Session Metrics Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Session**: {start_short} \u2014 {end_short} ({dur_str})  ",
        f"**Data**: `{summary.get('report_file', 'N/A')}`",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Total Events | {total} |",
        f"| LLM Calls | {summary['llm_calls']} |",
        f"| Human Interrupts | {summary['human_interrupts']} |",
        f"| **Autonomy Score** | **{summary['autonomy_score_pct']}%** |",
        f"| Estimated Context | {summary['estimated_context_tokens']:,} tokens |",
        f"| Context Utilization | {summary['context_utilization_pct']}%"
        f" of {summary['context_limit'] // 1000}K |",
        f"| Avg Tokens / Event | {summary['avg_tokens_per_event']:,} |",
        "",
        "> **Note**: Context estimates cover tool I/O only. Actual context usage",
        "> (including assistant responses and system prompts) is typically",
        "> 1.5\u20132.5\u00d7 higher.",
        "",
    ]

    # ── Tool Usage ────────────────────────────────────────────────────────
    lines += [
        "## Tool Usage",
        "",
        "| Tool | Count | % | Avg Output Tokens |",
        "|------|------:|--:|------------------:|",
    ]
    for t in summary["tool_breakdown"]:
        lines.append(
            f"| {t['tool']} | {t['count']} | {t['percentage']}%"
            f" | {t['avg_output_tokens']:,} |"
        )
    lines.append("")

    # ── Interrupt Timeline ────────────────────────────────────────────────
    interrupt_list = summary.get("interrupts", [])
    if interrupt_list:
        lines += [
            "## Interrupt Timeline",
            "",
            "Shows when the agent paused for human clarification.",
            "",
            "| # | At Event | Preceding Tool | Context at Interrupt"
            " | % Into Session |",
            "|--:|:--------:|:--------------:|---------------------:"
            "|:--------------:|",
        ]
        for i, intr in enumerate(interrupt_list, 1):
            cn = intr["at_event"]
            pct_into = round(cn / total * 100) if total else 0
            lines.append(
                f"| {i} | {cn} | {intr['preceding_tool']}"
                f" | {intr['context_tokens']:,} tokens | {pct_into}% |"
            )
        lines.append("")

    # ── Context Growth Segments ───────────────────────────────────────────
    interrupt_positions = [i for i, e in enumerate(events)
                          if e["event_type"] == "human_interrupt"]

    # Build segment boundaries (0-based indices into events list).
    boundaries: list[int] = [0]
    for pos in interrupt_positions:
        boundaries.append(pos + 1)
    boundaries.append(len(events))

    if len(boundaries) > 2:  # at least one interrupt → meaningful segments
        lines += [
            "## Context Growth Segments",
            "",
            "| Segment | Events | Tokens Added | Rate (tokens/event) |",
            "|---------|-------:|-------------:|--------------------:|",
        ]
        for j in range(len(boundaries) - 1):
            seg = events[boundaries[j]:boundaries[j + 1]]
            if not seg:
                continue
            tokens_added = sum(e["event_tokens"] for e in seg)
            count = len(seg)
            rate = round(tokens_added / count) if count else 0
            first_cn = seg[0]["call_number"]
            last_cn = seg[-1]["call_number"]
            if j == 0:
                label = f"Start \u2192 Event {last_cn}"
            elif j == len(boundaries) - 2:
                label = f"Event {first_cn} \u2192 End"
            else:
                label = f"Event {first_cn} \u2192 {last_cn}"
            lines.append(
                f"| {label} | {count} | {tokens_added:,} | {rate:,} |"
            )
        lines.append("")

    # ── Top Token Consumers ───────────────────────────────────────────────
    top_n = min(10, total)
    by_tokens = sorted(events, key=lambda e: e["event_tokens"], reverse=True)[:top_n]
    if by_tokens:
        lines += [
            "## Top Token Consumers",
            "",
            f"Events that added the most tokens to context (top {top_n}).",
            "",
            "| Event # | Tool | Event Tokens | Cumulative After |",
            "|--------:|:-----|-------------:|-----------------:|",
        ]
        for e in by_tokens:
            lines.append(
                f"| {e['call_number']} | {e['tool_name']}"
                f" | {e['event_tokens']:,}"
                f" | {e['cumulative_context_tokens']:,} |"
            )
        lines.append("")

    lines += [
        "---",
        "*Generated by session-metrics-tracker skill*",
        "",
    ]

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate session metrics report")
    parser.add_argument("--report-dir", default=None,
                        help="Output directory (default: .claude/reports/)")
    parser.add_argument("--input", default=None,
                        help="Path to JSONL metrics log")
    parser.add_argument("--format", choices=["csv", "json", "markdown"],
                        default="csv", dest="output_format",
                        help="Primary report format (default: csv)")
    parser.add_argument("--context-limit", type=int,
                        default=_DEFAULT_CONTEXT_LIMIT,
                        help="Model context window in tokens (default: 200000)")
    parser.add_argument("--reset", action="store_true",
                        help="Archive current session log and start fresh")
    args = parser.parse_args()

    report_dir = args.report_dir or os.path.join(os.getcwd(), ".claude", "reports")
    os.makedirs(report_dir, exist_ok=True)

    log_path = args.input or os.path.join(report_dir, "session-metrics-current.jsonl")
    state_path = os.path.join(report_dir, ".session-metrics-state.json")

    if not os.path.exists(log_path):
        print(json.dumps({"error": f"No metrics data found at {log_path}"}))
        sys.exit(1)

    raw_events = _load_events(log_path)
    if not raw_events:
        print(json.dumps({"error": "No events recorded in log"}))
        sys.exit(1)

    events = _enrich_events(raw_events)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Determine output paths.
    md_path = os.path.join(report_dir, f"session-report-{ts}.md")

    if args.output_format == "csv":
        primary_path = os.path.join(report_dir, f"session-report-{ts}.csv")
        summary = _compute_summary(events, primary_path, md_path, args.context_limit)
        _write_csv(events, primary_path)
        _write_markdown(events, summary, md_path)  # companion
    elif args.output_format == "json":
        primary_path = os.path.join(report_dir, f"session-report-{ts}.json")
        summary = _compute_summary(events, primary_path, md_path, args.context_limit)
        _write_json(events, summary, primary_path)
        _write_markdown(events, summary, md_path)  # companion
    else:  # markdown
        primary_path = md_path
        summary = _compute_summary(events, primary_path, None, args.context_limit)
        _write_markdown(events, summary, primary_path)

    print(json.dumps(summary, indent=2))

    # Archive and reset if requested.
    if args.reset:
        archive_path = os.path.join(
            report_dir, f"session-metrics-archived-{ts}.jsonl")
        shutil.move(log_path, archive_path)
        # Also clean up any legacy state file from old versions.
        if os.path.exists(state_path):
            os.remove(state_path)
        print(json.dumps({
            "reset": True,
            "archived_to": archive_path,
        }), file=sys.stderr)


if __name__ == "__main__":
    main()
