#!/usr/bin/env python3
"""
Silent PostToolUse hook — records one raw event per tool call.

Appends a single JSON line to session-metrics-current.jsonl.
No state file. No cumulative counters. No stdout.

All derived metrics (cumulative sums, elapsed time, call numbering)
are computed at report-generation time. This keeps the hot path to a
single atomic file append — no read-modify-write race, no lock needed.

Known limitation: context tracking only captures tool I/O (args + output).
The assistant's own response text and system prompts also consume context
but are not available to PostToolUse hooks. Actual context usage is
typically 1.5–2.5x the value reported here.
"""

import json
import os
import re
from datetime import datetime

# Tools whose invocation means the agent paused for human input.
_INTERRUPT_TOOLS = {"AskUserQuestion"}

# Token estimation ratios (characters per token), aligned with
# context-auto-summarizer/scripts/token_counter.py.
_STRUCTURED_RATIO = 2.5   # JSON, XML, YAML
_CODE_RATIO = 3.5
_TEXT_RATIO = 4.0

# Only inspect this many characters for content-type detection.
# Keeps cost constant regardless of output size.
_DETECTION_PREFIX_LEN = 512

# Compiled regex for code detection — matches whole words only,
# consistent with token_counter.py's approach.
_CODE_RE = re.compile(
    r'\b(?:function|class|def|var|let|const|import|export'
    r'|if|else|for|while|return|package|func|struct'
    r'|interface|async|from|require|using)\b'
    r'|[{};]'
    r'|^\s*(?:#|//)',
    re.MULTILINE,
)


def _estimate_tokens_structured(text: str) -> int:
    """Token estimate for known-structured text (JSON tool args)."""
    if not text:
        return 0
    return max(1, int(len(text) / _STRUCTURED_RATIO))


def _estimate_tokens(text: str) -> int:
    """Token estimate for unknown-format text (tool output).

    Checks only a prefix of the text for content-type classification,
    then applies the ratio to the full length.
    """
    if not text:
        return 0
    prefix = text[:_DETECTION_PREFIX_LEN]
    stripped = prefix.lstrip()
    # Structured data (JSON/XML) — starts with a structural char.
    if stripped[:1] in ("{", "[", "<"):
        return max(1, int(len(text) / _STRUCTURED_RATIO))
    # Source code — regex word-boundary check on a prefix.
    if _CODE_RE.search(prefix):
        return max(1, int(len(text) / _CODE_RATIO))
    # Default: natural language.
    return max(1, len(text) // 4)


def main() -> None:
    try:
        now = datetime.now()
        tool_name = os.environ.get("CLAUDE_TOOL_NAME", "unknown")
        tool_args = os.environ.get("CLAUDE_TOOL_ARGS", "")
        tool_output = os.environ.get("CLAUDE_TOOL_OUTPUT", "")

        report_dir = os.environ.get("SESSION_METRICS_DIR") or \
            os.path.join(os.getcwd(), ".claude", "reports")
        os.makedirs(report_dir, exist_ok=True)

        log_path = os.path.join(report_dir, "session-metrics-current.jsonl")

        # Tool args are always JSON → structured ratio.
        # Tool output format varies → heuristic detection.
        event = {
            "ts": now.isoformat(),
            "tool_name": tool_name,
            "event_type": "human_interrupt" if tool_name in _INTERRUPT_TOOLS else "llm_call",
            "args_tokens": _estimate_tokens_structured(tool_args),
            "output_tokens": _estimate_tokens(tool_output),
        }

        # Single atomic append — no state file, no locking needed.
        with open(log_path, "a") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")

    except Exception:
        # Swallow everything — this hook must never break the main process.
        pass


if __name__ == "__main__":
    main()
