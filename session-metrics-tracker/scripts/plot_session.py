#!/usr/bin/env python3
"""
Plot session metrics as a multi-panel line graph.

Accepts either a CSV report or a raw JSONL log as input.
Produces three subplots:
  1. Context length growth (with interrupt markers)
  2. Cumulative LLM calls vs human interrupts
  3. Per-event token consumption (bar chart, colored by event type)

Usage:
    python plot_session.py session-report-*.csv
    python plot_session.py session-metrics-current.jsonl
    python plot_session.py --report-dir .claude/reports/
    python plot_session.py --report-dir .claude/reports/ --output plot.png
    python plot_session.py --x-axis time                  # elapsed seconds

Requires: pip install matplotlib
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ── Data loading ─────────────────────────────────────────────────────────────

def _find_latest(report_dir: str, pattern: str) -> str | None:
    matches = sorted(Path(report_dir).glob(pattern))
    return str(matches[-1]) if matches else None


def _read_csv(path: str) -> list[dict]:
    """Read an enriched CSV report into a list of dicts."""
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append({
                "call_number": int(row["call_number"]),
                "elapsed_seconds": float(row.get("elapsed_seconds", 0)),
                "event_type": row["event_type"],
                "tool_name": row["tool_name"],
                "args_tokens": int(row.get("args_tokens", 0)),
                "output_tokens": int(row.get("output_tokens", 0)),
                "event_tokens": int(row.get("event_tokens",
                                   int(row.get("args_tokens", 0))
                                   + int(row.get("output_tokens", 0)))),
                "cumulative_context_tokens": int(row["cumulative_context_tokens"]),
                "cumulative_llm_calls": int(row["cumulative_llm_calls"]),
                "cumulative_interrupts": int(row["cumulative_interrupts"]),
            })
    return rows


def _read_jsonl(path: str) -> list[dict]:
    """Read raw JSONL and enrich with cumulative fields for plotting."""
    raw = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    raw.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    if not raw:
        return []

    start_ts = datetime.fromisoformat(raw[0]["ts"])
    cum_ctx = cum_llm = cum_int = 0
    enriched = []
    for i, e in enumerate(raw, 1):
        evt_ts = datetime.fromisoformat(e["ts"])
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
            "elapsed_seconds": round((evt_ts - start_ts).total_seconds(), 1),
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


def _load_data(path: str) -> list[dict]:
    """Auto-detect format (CSV or JSONL) and load."""
    if path.endswith(".csv"):
        return _read_csv(path)
    return _read_jsonl(path)


# ── Plotting ─────────────────────────────────────────────────────────────────

def _plot(data: list[dict], output: str | None, x_axis: str) -> None:
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("matplotlib is required: pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    # Select x-axis values.
    if x_axis == "time":
        xs = [d["elapsed_seconds"] for d in data]
        x_label = "Elapsed Time (seconds)"
    else:
        xs = [d["call_number"] for d in data]
        x_label = "Event Number"

    ctx_k = [d["cumulative_context_tokens"] / 1000 for d in data]
    llm = [d["cumulative_llm_calls"] for d in data]
    interrupts = [d["cumulative_interrupts"] for d in data]
    event_tokens = [d["event_tokens"] for d in data]
    event_types = [d["event_type"] for d in data]

    # Interrupt markers.
    int_x = [x for x, t in zip(xs, event_types) if t == "human_interrupt"]
    int_ctx = [k for k, t in zip(ctx_k, event_types) if t == "human_interrupt"]

    # Bar colors by event type.
    bar_colors = ["#dc2626" if t == "human_interrupt" else "#16a34a"
                  for t in event_types]

    # ── Figure ────────────────────────────────────────────────────────────
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle("Claude Code Session Metrics", fontsize=14, fontweight="bold")

    # ── Subplot 1: Context growth ─────────────────────────────────────────
    ax1.plot(xs, ctx_k, color="#2563eb", linewidth=1.5,
             label="Context (K tokens)")
    ax1.fill_between(xs, ctx_k, alpha=0.08, color="#2563eb")
    if int_x:
        ax1.scatter(int_x, int_ctx, color="#dc2626", marker="v", s=50,
                    zorder=5, label="Human interrupt")
    ax1.set_ylabel("Estimated Tokens (K)")
    ax1.set_title("Context Length Growth")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(True, alpha=0.25)

    # ── Subplot 2: LLM calls vs interrupts ────────────────────────────────
    ax2.plot(xs, llm, color="#16a34a", linewidth=1.5, label="LLM Calls")
    ax2.plot(xs, interrupts, color="#dc2626", linewidth=1.5,
             label="Human Interrupts")
    ax2.set_ylabel("Cumulative Count")
    ax2.set_title("LLM Calls vs Human Interrupts")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.25)
    # Ratio annotation.
    final_llm = llm[-1] if llm else 0
    final_int = interrupts[-1] if interrupts else 0
    total = len(data)
    autonomy = round(final_llm / total * 100, 1) if total else 0
    ax2.annotate(
        f"LLM : Human = {final_llm}:{final_int}  |  Autonomy {autonomy}%",
        xy=(0.98, 0.04), xycoords="axes fraction",
        ha="right", va="bottom", fontsize=9, fontstyle="italic",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fef9c3", alpha=0.85),
    )

    # ── Subplot 3: Per-event token consumption ────────────────────────────
    ax3.bar(xs, event_tokens, color=bar_colors, width=0.8, alpha=0.85)
    ax3.set_xlabel(x_label)
    ax3.set_ylabel("Tokens")
    ax3.set_title("Per-Event Token Consumption")
    ax3.grid(True, axis="y", alpha=0.25)
    # Legend for bar colors.
    from matplotlib.patches import Patch
    ax3.legend(
        handles=[Patch(facecolor="#16a34a", label="LLM Call"),
                 Patch(facecolor="#dc2626", label="Human Interrupt")],
        loc="upper right", fontsize=9,
    )

    # ── Session summary text box ──────────────────────────────────────────
    summary_text = (
        f"Events: {total}   |   "
        f"Context: {ctx_k[-1]:.1f}K tokens   |   "
        f"Duration: {data[-1]['elapsed_seconds']:.0f}s"
    )
    fig.text(0.5, 0.01, summary_text, ha="center", fontsize=9,
             fontstyle="italic", color="#666666")

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])

    if output:
        plt.savefig(output, dpi=150, bbox_inches="tight")
        print(f"Plot saved to {output}")
    else:
        plt.show()


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot session metrics as a multi-panel line graph")
    parser.add_argument("input_file", nargs="?",
                        help="Path to CSV report or JSONL log")
    parser.add_argument("--report-dir", default=None,
                        help="Directory to find the latest report")
    parser.add_argument("--output", default=None,
                        help="Save plot to file (PNG/PDF/SVG)")
    parser.add_argument("--x-axis", choices=["event", "time"], default="event",
                        help="X-axis: event number (default) or elapsed time")
    args = parser.parse_args()

    # Resolve input path.
    if args.input_file:
        data_path = args.input_file
    else:
        report_dir = args.report_dir or os.path.join(
            os.getcwd(), ".claude", "reports")
        # Prefer CSV reports, fall back to raw JSONL.
        data_path = (_find_latest(report_dir, "session-report-*.csv")
                     or _find_latest(report_dir, "session-metrics-current.jsonl"))
        if not data_path:
            print("No session report or log file found.", file=sys.stderr)
            sys.exit(1)

    if not os.path.exists(data_path):
        print(f"File not found: {data_path}", file=sys.stderr)
        sys.exit(1)

    data = _load_data(data_path)
    if not data:
        print("No data points found.", file=sys.stderr)
        sys.exit(1)

    _plot(data, args.output, args.x_axis)


if __name__ == "__main__":
    main()
