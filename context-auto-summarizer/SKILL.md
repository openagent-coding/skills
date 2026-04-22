---
name: context-auto-summarizer
description: "Automatic context window management with intelligent summarization and affinity clustering. Monitor token usage after every tool call using scripts/token_counter.py and trigger summarization at 90% threshold. Use for long coding sessions, research workflows, multi-step tasks, and any scenario where context preservation matters. Activate this skill when working on tasks that involve many tool calls, large file reads, or extended conversations that risk filling the context window."
---

# Context Auto-Summarizer

Instruction-based context management that monitors token usage after every tool call and performs affinity-based summarization when thresholds are exceeded. Works alongside Claude Code's built-in compaction.

## How It Works

1. After every tool call, estimate current token usage with `scripts/token_counter.py`
2. When usage exceeds 90%, analyze conversation structure with `scripts/affinity_clusterer.py`
3. Use the affinity chart to identify low-priority content, then trigger `/compact` targeting under 60% usage

## Context Monitoring Procedure

After every tool call, run a token count check:

```bash
python scripts/token_counter.py --text "<current conversation text>" --model claude-4-sonnet
```

Check the output:
- If `exceeds_90_percent` is `false`: continue normally
- If `exceeds_90_percent` is `true`: proceed to Summarization Procedure

Do NOT instantiate summarization before the threshold is crossed. The monitoring step is lightweight and should not interrupt workflow.

## Summarization Procedure

When the 90% threshold is exceeded:

### Step 1: Cluster the conversation

```bash
python scripts/affinity_clusterer.py --input conversation.txt --threshold 0.8 --output clusters.json
```

### Step 2: Review the affinity chart

Read `clusters.json` and identify:
- **High-affinity clusters** (score >= 0.8): preserve these
- **Low-affinity clusters** (score < 0.8): candidates for summarization
- **Code changes map**: track which files were modified and their cluster relationships

### Step 3: Identify content to preserve unconditionally

Never summarize:
- User prompts (all of them)
- System prompts
- Last 3 conversation turns (recent context)

### Step 4: Compact with focus

Run `/compact` with explicit instructions to:
- Preserve all user and system prompts verbatim
- Keep recent turns intact
- Keep high-affinity cluster content
- Summarize low-affinity clusters
- Target under 60% of context limit

Example: `/compact preserve user prompts, system prompts, last 3 turns, and high-affinity code change clusters. Summarize low-affinity diagnostic output and verbose tool results. Target under 60% context usage.`

## Content Preservation Priority

```
Priority 1: User prompts (always preserved verbatim)
Priority 2: System prompts (always preserved verbatim)
Priority 3: Recent turns (last 3 by default)
Priority 4: High-affinity clusters (>= 0.8 similarity score)
Priority 5: Code changes and tool operations
Priority 6: Error messages and debugging context
Priority 7: Research results and documentation
Priority 8: Tool diagnostics and verbose output
```

## Scripts

### token_counter.py

Estimate token count for text content.

```bash
# From text
python scripts/token_counter.py --text "content to analyze"

# From file
python scripts/token_counter.py --file conversation.txt --model claude-4-sonnet

# From stdin
cat conversation.txt | python scripts/token_counter.py
```

Output: JSON with `estimated_tokens`, `model`, `context_limit`, `usage_percentage`, `exceeds_90_percent`.

### affinity_clusterer.py

Group conversation segments by semantic similarity and generate code change maps.

```bash
# Cluster with default threshold (0.8)
python scripts/affinity_clusterer.py --input conversation.txt

# Custom threshold and output file
python scripts/affinity_clusterer.py --input conversation.txt --threshold 0.7 --output clusters.json

# Minimum cluster size
python scripts/affinity_clusterer.py --input conversation.txt --min-size 3
```

Output: JSON with `summary` (segment/cluster counts, affinity distribution), `clusters` (with segment IDs, affinity scores, code changes), and `code_changes_map` (file paths mapped to cluster relationships).

## Integration with Claude Code

This skill complements Claude Code's built-in compaction:

- **Built-in compaction**: Triggers automatically at ~75-92% capacity
- **This skill**: Provides earlier detection (90%), structured analysis via affinity clustering, and guided `/compact` invocations that preserve the most important content
- **`/compact` command**: Use for manual compaction with a custom focus description

## Reference

See `references/context_management_guide.md` for model context limits, token estimation ratios, threshold recommendations by workflow, and detailed integration notes.
