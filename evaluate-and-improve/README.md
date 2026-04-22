# Evaluate and Improve

Evaluate completed agent work against quality standards and automatically retry targeted fixes when scores fall below a configurable threshold.

## Overview

This skill scores agent outputs across five quality dimensions, generates a detailed report, and runs an automated feedback loop -- re-running targeted fixes on failing categories up to a configurable number of retries before asking the user.

## When to Use

- After multi-agent task completion to validate results
- When you want quality assurance on completed work
- To check whether agent output meets a minimum quality bar

## Quality Dimensions (each scored 1-5)

| Dimension | What It Measures |
|-----------|-----------------|
| Completeness | Are all requirements addressed? |
| Groundedness | Does the output match the requested context? |
| Technical Quality | Code quality, best practices, correctness |
| Agent Compliance | Adherence to agent-specific standards |
| User Value | Is the output ready to use? |

## Configuration

| Setting | Default | Flag |
|---------|---------|------|
| Fail threshold | 3 | `--threshold=N` (1-5) |
| Max auto-retries | 2 | `--retries=N` (0-10) |
| Interactive mode | off | `--interactive` |

## Usage

```
/evaluate-and-improve                    # Evaluate most recent completed task
/evaluate-and-improve 42                 # Evaluate task #42
/evaluate-and-improve python-dev         # Evaluate latest python-dev work
/evaluate-and-improve --threshold=4      # Stricter quality bar
/evaluate-and-improve --retries=0        # Evaluate only, no auto-fix
```

## Workflow

1. **Identify** the completed task and its modified files
2. **Evaluate** against agent-specific checklists from `references/quality-rubric.md`
3. **Score** each dimension and determine verdict (EXCELLENT / PASS / CONDITIONAL PASS / FAIL)
4. **Analyze prompt** quality if scores are low (one-time, iteration 0 only)
5. **Fix loop** -- launch targeted fix agents for failing categories, re-evaluate, track regressions
6. **Report** -- write final consolidated report to `.claude/reports/`

## Verdicts

- **EXCELLENT**: All scores >= 4, average >= 4.5
- **PASS**: All scores >= 3, average >= 3.5
- **CONDITIONAL PASS**: All scores >= 2, average >= 2.5
- **FAIL**: Any score < 2 or average < 2.5

## References

- [Quality rubric and agent checklists](references/quality-rubric.md)
- [Score parsing script](scripts/parse_scores.sh)