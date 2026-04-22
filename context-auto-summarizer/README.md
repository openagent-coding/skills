# Context Auto-Summarizer

Automatic context window management for AI coding agents. Monitors token usage passively via a PostToolUse hook and triggers intelligent, affinity-based compaction before the context window fills up.

## What It Does

Long coding sessions accumulate context -- file reads, tool results, research output -- until the agent hits its context limit and loses important earlier work. This skill:

1. **Monitors** token usage after every Nth tool call by reading the session transcript
2. **Warns** at 80% capacity so you know compaction is coming
3. **Triggers compaction** at 88% with affinity-based guidance that preserves high-value content and summarizes low-value content
4. **Clusters** conversation segments by semantic similarity so compaction targets the right things

## Components

```
scripts/
  context_monitor_hook.py   # PostToolUse hook -- the main entry point
  affinity_clusterer.py     # Groups conversation segments by semantic similarity
  token_counter.py          # Lightweight token estimation (no external deps)
references/
  context_management_guide.md  # Thresholds, model limits, integration notes
SKILL.md                    # Skill definition for Claude Code
```

### context_monitor_hook.py

The PostToolUse hook. Runs after every tool call, checks the transcript every 3rd call to stay fast, and emits warnings/compaction instructions to stderr when thresholds are crossed. Tracks state per session to avoid duplicate alerts. Resets automatically after manual `/compact`.

### affinity_clusterer.py

Groups conversation segments into clusters using a weighted similarity score:
- **40%** cosine similarity (lightweight feature vectors, no ML dependencies)
- **30%** Jaccard word overlap (with stop-word filtering)
- **20%** segment type similarity (e.g., tool_use pairs with tool_result)
- **10%** proximity (segments close together are more related)

Supports both JSONL (Claude Code native) and plain text input formats. Outputs JSON with cluster summaries, affinity scores, and a code changes map.

### token_counter.py

Estimates token counts using character-ratio heuristics (no tokenizer library needed):
- English prose: ~4 chars/token
- Source code: ~3.5 chars/token
- Structured data (JSON/XML): ~2.5 chars/token

## Setup

### Claude Code

Add a `PostToolUse` hook to your project or user settings.

**Project-level** (`.claude/settings.json` in your repo):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "type": "command",
        "command": "python3 /path/to/skills/context-auto-summarizer/scripts/context_monitor_hook.py"
      }
    ]
  }
}
```

**User-level** (`~/.claude/settings.json`):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "type": "command",
        "command": "python3 ~/.claude/skills/context-auto-summarizer/scripts/context_monitor_hook.py"
      }
    ]
  }
}
```

### Cursor

Add a `postToolUse` hook in your Cursor hooks configuration.

**Project-level** (`.cursor/hooks.json` in your repo):

```json
{
  "version": 1,
  "hooks": {
    "postToolUse": [
      {
        "command": "python3 /path/to/skills/context-auto-summarizer/scripts/context_monitor_hook.py"
      }
    ]
  }
}
```

**Global** (`~/.cursor/hooks.json`):

```json
{
  "version": 1,
  "hooks": {
    "postToolUse": [
      {
        "command": "python3 ~/.claude/skills/context-auto-summarizer/scripts/context_monitor_hook.py"
      }
    ]
  }
}
```

> **Note:** Replace `/path/to/skills/` with the actual path where you cloned or installed this skill. The hook requires Python 3.8+ and has no external dependencies.

## Thresholds

| Threshold | Action |
|-----------|--------|
| 80% | Warning emitted to stderr |
| 88% | Compaction instruction emitted with affinity clustering guidance |
| < 72% | Flags reset (allows re-triggering after manual `/compact`) |

These are configurable by editing `WARN_THRESHOLD`, `COMPACT_THRESHOLD`, and the reset factor in `context_monitor_hook.py`.

## How Compaction Works

When the 88% threshold is hit, the hook instructs the agent to:

1. Export the conversation from the transcript
2. Run the affinity clusterer to group related segments
3. Use `/compact` with targeted instructions -- preserve high-affinity clusters and recent turns, summarize low-affinity content, target under 60% usage

Content preservation priority (highest to lowest):
1. User prompts (never summarized)
2. System prompts (never summarized)
3. Recent turns (last 3)
4. High-affinity clusters (score >= 0.8)
5. Code changes and tool operations
6. Error messages and debugging context
7. Research results and documentation
8. Tool diagnostics and verbose output

## Dependencies

None. All scripts use Python standard library only.