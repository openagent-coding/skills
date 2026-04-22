# Context Management Guide

## Model Context Limits

| Model | Standard Context | Extended Context |
|-------|-----------------|-----------------|
| Claude 4 Haiku | 200K tokens | - |
| Claude 4 Sonnet | 200K tokens | - |
| Claude 4 Opus | 200K tokens | - |
| Claude 4.5 Haiku | 200K tokens | - |
| Claude 4.5 Sonnet | 200K tokens | 1M tokens (beta) |
| Claude 4.5 Opus | 200K tokens | 1M tokens (beta) |
| Claude 4.6 Opus | 200K tokens | 1M tokens (beta) |

All models support up to 64K output tokens.

## Token Estimation Ratios

| Content Type | Chars per Token | Detection |
|-------------|----------------|-----------|
| English prose | ~4 | Default |
| Source code | ~3.5 | Keywords: `function`, `class`, `def`, `import`; symbols: `{};` |
| Structured data | ~2.5 | Starts with `{`, `[`, or `<` |

## Threshold Recommendations

### By Workflow

| Workflow | Trigger | Target | Affinity | Preserve Turns |
|----------|---------|--------|----------|---------------|
| Code development | 85% | 60% | 0.8 | 3 |
| Research session | 90% | 50% | 0.7 | 2 |
| Mixed / general | 85% | 55% | 0.75 | 3 |
| Emergency | 95% | 40% | 0.6 | 1 |

### Affinity Threshold Guide

- **0.8** (default): Preserves strongly related content, good for code sessions
- **0.7**: More aggressive compression, suitable for research with many tangents
- **0.6**: Emergency compression, preserves only the most tightly coupled segments

## Claude Code Integration

### Built-in Compaction
Claude Code has automatic compaction that triggers when context usage reaches approximately 75-92% of capacity. This skill complements it by providing earlier detection and structured analysis.

### `/compact` Command
Use `/compact [focus]` to manually trigger compaction with an optional focus description. Example: `/compact preserve code changes and error context`.

### PostToolUse Hooks
The `PostToolUse` hook fires after every tool call, making it the correct integration point for token monitoring. Configure in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "command": "python path/to/token_counter.py --file $CONVERSATION_FILE"
      }
    ]
  }
}
```

## Content Preservation Priority

1. User prompts (never summarize)
2. System prompts (never summarize)
3. Recent turns (last 3 by default)
4. High-affinity clusters (above threshold)
5. Code changes and tool operations
6. Error messages and debugging context
7. Research results and documentation
8. Tool diagnostics and verbose output
