#!/usr/bin/env python3
"""
Context Monitor Hook — passive PostToolUse hook that reads token usage
from the transcript JSONL and signals Claude to run /compact with
affinity-based guidance when context is getting full.
"""

import hashlib
import json
import os
import sys
from glob import glob
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from hook_utils import STATE_DIR, FileLock, read_hook_payload
except Exception:
    sys.exit(0)

SKILL_DIR = Path.home() / ".claude" / "skills" / "context-auto-summarizer"
CLUSTERER = SKILL_DIR / "scripts" / "affinity_clusterer.py"

MODEL_CONTEXT_LIMITS = {
    "[1m]": 1_000_000,
}
DEFAULT_CONTEXT_LIMIT = 200_000

WARN_THRESHOLD = 0.80
COMPACT_THRESHOLD = 0.88
CHECK_EVERY_N_CALLS = 3


def _state_path(session_id: str) -> Path:
    h = hashlib.sha256(session_id.encode()).hexdigest()[:16]
    return STATE_DIR / f"ctxmon_{h}.json"


def _lock_path(session_id: str) -> Path:
    h = hashlib.sha256(session_id.encode()).hexdigest()[:16]
    return STATE_DIR / f"ctxmon_{h}.lock"


def _load(session_id: str) -> Dict[str, Any]:
    p = _state_path(session_id)
    try:
        if p.exists():
            return json.loads(p.read_text())
    except Exception:
        pass
    return {"calls": 0, "warned": False, "compacted": False}


def _save(session_id: str, state: Dict[str, Any]) -> None:
    p = _state_path(session_id)
    try:
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        os.replace(tmp, p)
    except Exception:
        pass


def _context_limit() -> int:
    model = os.environ.get("CLAUDE_MODEL", "")
    for marker, limit in MODEL_CONTEXT_LIMITS.items():
        if marker in model:
            return limit
    return DEFAULT_CONTEXT_LIMIT


def _find_transcript(session_id: str) -> Optional[Path]:
    """Find the transcript JSONL for this session."""
    base = Path.home() / ".claude" / "projects"
    matches = list(base.rglob(f"{session_id}.jsonl"))
    if matches:
        return matches[0]
    return None


def _last_usage(transcript: Path) -> Tuple[int, str]:
    """Read the last assistant message's usage from the transcript.

    Returns (total_context_tokens, model_name).
    Total = input_tokens + cache_creation_input_tokens + cache_read_input_tokens
    which represents the full context window consumption.
    """
    last_total = 0
    last_model = ""
    try:
        with open(transcript, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                if msg.get("type") != "assistant":
                    continue
                m = msg.get("message", {})
                usage = m.get("usage")
                if not isinstance(usage, dict):
                    continue
                total = (
                    usage.get("input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                )
                if total > 0:
                    last_total = total
                    last_model = m.get("model", "")
    except Exception:
        pass
    return last_total, last_model


def main() -> int:
    payload = read_hook_payload()
    if payload.get("hook_event_name") != "PostToolUse":
        return 0

    session_id = payload.get("session_id", "")
    if not session_id:
        return 0

    with FileLock(_lock_path(session_id)):
        state = _load(session_id)
        state["calls"] = state.get("calls", 0) + 1

        # Only check transcript every N calls to stay fast
        if state["calls"] % CHECK_EVERY_N_CALLS != 0:
            _save(session_id, state)
            return 0

        transcript = _find_transcript(session_id)
        if not transcript:
            _save(session_id, state)
            return 0

        total_tokens, model = _last_usage(transcript)
        if total_tokens <= 0:
            _save(session_id, state)
            return 0

        limit = _context_limit()
        pct = total_tokens / limit

        if pct >= COMPACT_THRESHOLD and not state.get("compacted"):
            state["compacted"] = True
            state["warned"] = True
            _save(session_id, state)

            # Output compact instruction to stderr — Claude sees this
            print(
                f"⚠️  Context at {pct:.0%} ({total_tokens:,}/{limit:,} tokens). "
                f"Run the affinity clusterer to guide compaction:\n"
                f"  1. Export conversation to a temp file from {transcript}\n"
                f"  2. Run: python3 {CLUSTERER} --input <file> --threshold 0.7\n"
                f"  3. Use the cluster output to run /compact — preserve high-affinity "
                f"clusters and recent turns, summarize low-affinity content. "
                f"Target under 60% context usage.",
                file=sys.stderr,
            )
            return 0

        if pct >= WARN_THRESHOLD and not state.get("warned"):
            state["warned"] = True
            _save(session_id, state)

            print(
                f"ℹ️  Context at {pct:.0%} ({total_tokens:,}/{limit:,} tokens). "
                f"Approaching limit — /compact will be triggered at {COMPACT_THRESHOLD:.0%}.",
                file=sys.stderr,
            )
            return 0

        # Reset flags if usage drops (e.g. after a manual /compact)
        if pct < WARN_THRESHOLD * 0.9:
            state["warned"] = False
            state["compacted"] = False

        _save(session_id, state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
