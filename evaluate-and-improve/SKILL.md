---
name: evaluate-and-improve
description: "Evaluate agent outputs against quality standards and automatically retry targeted fixes when any category scores below threshold (default 3/5, configurable via --threshold). Generates a report at .claude/reports/. Use when: (1) user says 'evaluate output', 'evaluate and improve', 'check quality', 'rerun if quality does not meet standards', 'improve the output', (2) user explicitly runs /evaluate-and-improve, (3) after multi-agent task completion to validate results, or (4) user wants quality assurance on completed work."
---

# Evaluate and Improve

Evaluate completed agent work against quality standards, generate a report, and automatically re-run targeted fixes on categories scoring below a configurable threshold (default 3/5) — with configurable automatic retries (default 2) before asking the user.

## Configuration

| Setting             | Default | Override via arguments         | Valid range |
|---------------------|---------|--------------------------------|-------------|
| Fail threshold      | 3       | `--threshold=N` (score < N triggers retry) | 1-5 |
| Max auto-retries    | 2       | `--retries=N`                  | 0-10 (0 = evaluate-only, no auto-fix) |
| Interactive mode    | off     | `--interactive`                | flag |

When not overridden, use the defaults above. Throughout this document, `THRESHOLD` refers to the configured fail threshold and `MAX_RETRIES` refers to the configured max auto-retries.

**Argument validation**: If `--threshold` is outside 1-5 or `--retries` is outside 0-10 or either is non-integer, warn the user and fall back to defaults. If `--retries=0`, run evaluation only — skip the feedback loop entirely and proceed to Step 6 after scoring.

## Error Handling

Apply these rules at every step. If any step fails, do not silently continue — always inform the user.

| Failure                          | Action                                                                 |
|----------------------------------|------------------------------------------------------------------------|
| No completed task found          | Tell the user no recent completed task exists. Ask them to specify a task ID. |
| Evaluation subagent crashes/times out | Inform the user. Offer to retry the evaluation or abort.            |
| Fix subagent crashes/times out   | Inform the user with the iteration number. Offer to retry or accept current quality. |
| Report file fails to write       | Write report to `/tmp/evaluation-<timestamp>.md` as fallback. Warn the user. |
| Referenced files no longer exist | Skip missing files. Note them in the report under Findings > Issues. Reduce Completeness score accordingly. |
| Score regression after fix pass  | Flag the regression in the progress summary. Do NOT update `BEST_SCORES` for regressed categories — keep the previous best value. Warn the user. Use `CURRENT_SCORES` (not `BEST_SCORES`) for the final verdict. |
| State file missing or corrupt    | Re-initialize state from the latest report file scores. Warn the user. |
| Parse script fails               | Fall back to Grep-based extraction (last match of `<!-- SCORES:` pattern). |

## Workflow

1. Identify work to evaluate
2. Run evaluation and generate report
3. Parse scores and check thresholds
4. Prompt evaluation (if any score < THRESHOLD)
5. Feedback loop (auto-retry up to MAX_RETRIES, then ask user)
6. Write final consolidated report with summary

## Step 1: Identify Work

**Argument parsing** — extract flags first, then resolve target in this order (first match wins):
1. `--threshold=N`, `--retries=N`, `--interactive` → extract and remove from arguments before target resolution
2. `latest` keyword → most recently completed task
3. Numeric string → treat as task ID, fetch with `TaskGet`
4. Known agent name (`python-dev`, `go-developer`, `devops`, `tech-writer`, `code-analyzer`, `test-planner`, `software-architect`, `general-purpose`) → find most recent completed task by that agent
5. Other string → search task subjects/descriptions for a substring match

If `$ARGUMENTS` provided:
- Parse using the precedence above
- Use `TaskGet` to retrieve full task details

If no arguments:
- Use `TaskList` to find the most recently completed task
- If no completed task exists, inform the user and ask them to specify a task ID (see Error Handling)
- Identify which agent produced the work and what files were created/modified

Collect:
- **Agent type** (`python-dev`, `go-developer`, `devops`, `tech-writer`, `code-analyzer`, `test-planner`, `software-architect`, `general-purpose`). If the agent type cannot be determined from task metadata, default to `general-purpose` for evaluation and fix passes.
- **Modified files** — determine files changed by the task using this priority:
  1. Task description/metadata file list (if the task explicitly lists files)
  2. `git log --format='' --name-only` scoped to commits matching the task (by message or time range)
  3. `git diff --name-only $(git log --oneline -20 --format='%H' | tail -1)..HEAD` as a broader fallback
  4. `Glob` as a last resort if git history is unavailable
  Cross-reference results with the task description to filter out unrelated changes.
- **Original user requirements** (from task description)
- **Baseline commit** — record the current `HEAD` SHA: `BASELINE_SHA=$(git rev-parse HEAD)`. This is used for scoped re-evaluation in later iterations.

## Step 2: Run Evaluation

Before the first evaluation, generate paths and reuse them for all iterations:
```
REPORT_PATH=.claude/reports/evaluation-<YYYYMMDD-HHMMSS>.md
ITERATIONS_PATH=.claude/reports/evaluation-<YYYYMMDD-HHMMSS>.iterations.md
STATE_PATH=.claude/reports/evaluation-<YYYYMMDD-HHMMSS>.state.json
```

Create the reports directory: run `mkdir -p .claude/reports/` via Bash. If this fails (permissions, disk full), use `/tmp/evaluation-<YYYYMMDD-HHMMSS>.*` as fallback and warn the user.

**Initialize the state file** (`STATE_PATH`) with:
```json
{
  "iteration": 0,
  "best_scores": {},
  "current_scores": {},
  "previous_scores": {},
  "prompt_verdict": "",
  "suggested_prompt": "",
  "baseline_sha": "<BASELINE_SHA>",
  "report_path": "<REPORT_PATH>",
  "iterations_path": "<ITERATIONS_PATH>",
  "files": ["<file list>"],
  "agent_type": "<agent-type>",
  "task_description": "<task description>"
}
```

Launch a Task agent (`subagent_type=general-purpose`) with the following prompt. Note: the agent-specific checklist is included inline to avoid a redundant file read on every iteration — extract the relevant checklist from `references/quality-rubric.md` once and embed it.

```
Evaluate the following agent work.

Agent: [agent-type]
Task: [task description]
Files to review: [file list]

## Scoring Dimensions (rate each 1-5)

- **Completeness**: 1=Major requirements missing, 3=Most met, 5=All fully addressed
- **Groundedness**: 1=Major deviation from context, 3=Mostly aligns, 5=Everything matches
- **Technical Quality**: 1=Poor quality many issues, 3=Acceptable some issues, 5=Excellent best practices
- **Agent Compliance**: 1=Major deviations from standards, 3=Most standards followed, 5=Exemplary adherence
- **User Value**: 1=Not usable, 3=Usable with modifications, 5=Ready to use exceeds expectations

## Agent-Specific Checklist ([agent-type])

[Paste the relevant checklist items from quality-rubric.md here]

## Verdict Criteria (evaluate top-down, first match applies)

- EXCELLENT: All scores >= 4 AND average >= 4.5
- PASS: All scores >= 3 AND average >= 3.5
- CONDITIONAL PASS: All scores >= 2 AND average >= 2.5
- FAIL: Any score < 2 OR average < 2.5

## Instructions

For each file, read it and assess against the agent-specific checklist.
Score each of the 5 dimensions on 1-5.

Write the evaluation report to: [ITERATIONS_PATH]
Use the iteration report format (Iteration 0 — Initial Evaluation).

IMPORTANT: At the very end of your output, append a machine-readable scores block
on a single line, exactly in this format (no extra spaces or formatting):

<!-- SCORES:{"completeness":N,"groundedness":N,"technical_quality":N,"agent_compliance":N,"user_value":N} -->

where N is the integer score 1-5 for each dimension.
```

**Re-evaluations during the feedback loop** (Step 5) — append to `ITERATIONS_PATH`. Do not overwrite previous iterations.

## Step 3: Parse Scores

After the evaluation completes, extract scores using the helper script:

```bash
bash .claude/skills/evaluate-and-improve/scripts/parse_scores.sh <ITERATIONS_PATH>
```

This extracts the **last** `<!-- SCORES:{...} -->` line and outputs clean JSON. If the script fails (exit code != 0), fall back to `Grep` with pattern `<!-- SCORES:` on the iterations file and take the **last match**, then strip the HTML comment wrapper to get the JSON.

Parse the JSON object to get scores for: `completeness`, `groundedness`, `technical_quality`, `agent_compliance`, `user_value`.

Identify:
- **Failing categories**: any score < `THRESHOLD`
- **Average score**: mean of all 5
- **Verdict**: EXCELLENT / PASS / CONDITIONAL PASS / FAIL (see verdict criteria above)

Update the state file:
- Set `current_scores` to the parsed scores
- Set `best_scores` to the parsed scores (initial evaluation — no prior data)
- Set `previous_scores` to `{}`

If all scores >= `THRESHOLD` and verdict is PASS or EXCELLENT, skip to Step 6.

If `MAX_RETRIES` is 0 (evaluate-only mode), skip to Step 6 regardless of scores.

## Step 4: Prompt Evaluation

Run only once on the initial evaluation (iteration 0) when any output score is < `THRESHOLD`. Do not re-run prompt analysis on retries.

Analyze the original user prompt/task description against the prompt evaluation rubric in `references/quality-rubric.md`.

Score 5 dimensions: **Specificity**, **Context**, **Constraints**, **Actionability**, **Scope** (each 1-5).

Then apply the conditional Examples recommendation logic:
- Check whether output failures (Groundedness < `THRESHOLD`, Agent Compliance < `THRESHOLD`, Completeness < `THRESHOLD`) trace back to prompt ambiguity
- If so, recommend the user include examples in future prompts and generate a sample example
- If failures were purely technical, skip the examples recommendation

Generate a **Prompt Verdict** (STRONG / ADEQUATE / WEAK / POOR).

**Persist these values** to the state file (`STATE_PATH`):
- `prompt_verdict` — the verdict string
- `suggested_prompt` — the rewritten prompt (empty string if verdict is STRONG/ADEQUATE)

If verdict is WEAK or POOR:
- Generate a rewritten improved prompt using the template in the rubric
- Include the prompt analysis and suggested rewrite in the iterations log
- Present the improved prompt to the user before the targeted fix pass so they can decide whether to use it

If verdict is STRONG or ADEQUATE:
- Note in the iterations log that prompt quality was not a contributing factor
- Proceed directly to the feedback loop

## Step 5: Feedback Loop

Read current state from `STATE_PATH`. Track iteration count, `BEST_SCORES`, `CURRENT_SCORES`, and `PREVIOUS_SCORES` via the state file — this ensures resilience if the conversation context is summarized.

**If any score < THRESHOLD AND iteration < MAX_RETRIES** (automatic retry):

1. Increment iteration count in the state file
2. Save `CURRENT_SCORES` as `PREVIOUS_SCORES` in the state file
3. **Scope the fix**: Run `git diff --name-only <BASELINE_SHA>..HEAD` to determine which files were modified since the last evaluation. If no files changed (fix agent didn't modify anything), warn the user and skip to the user decision point.
4. Launch a targeted fix Task agent (`subagent_type` matching the original agent type, or `general-purpose` if unknown) with prompt:
   ```
   The following categories scored below [THRESHOLD]/5 in quality evaluation.
   Fix ONLY these specific issues — do not refactor unrelated code.

   Failing categories:
   - [Category]: scored [X]/5 — [specific feedback from report]
   - [Category]: scored [X]/5 — [specific feedback from report]

   Previously passing categories (DO NOT regress these):
   - [Category]: [X]/5
   - [Category]: [X]/5

   Files to fix: [file list]
   Original requirements: [task description]
   ```
5. After fix completes, determine which files were actually changed by the fix: run `git diff --name-only` against the pre-fix state.
6. Re-run evaluation, but **scope it to changed files only**. Use `ITERATIONS_PATH` for output. Include in the evaluation prompt: "The following files were not modified since the last evaluation — carry forward their previous scores: [unchanged files]. Only re-evaluate: [changed files]."
7. Parse new scores from `ITERATIONS_PATH` using the parse script.
8. **Regression check**: Compare new scores against `PREVIOUS_SCORES`. For each category:
   - If a previously-passing category (>= THRESHOLD) dropped below THRESHOLD, flag it as a **regression**.
   - If any regression is detected, warn the user in the progress summary and do NOT update `BEST_SCORES` for regressed categories — keep the previous best value.
   - Update `BEST_SCORES` only for categories that improved or stayed the same.
   - Always update `CURRENT_SCORES` to reflect the actual current state.
9. Update the state file with new `BEST_SCORES`, `CURRENT_SCORES`, `PREVIOUS_SCORES`, and iteration count.
10. Output a progress summary to the user after each iteration:
    ```
    Iteration [N]: [Category] [old]/5 -> [new]/5, [Category] [old]/5 -> [new]/5.
    [If regression: "Warning: Regression: [Category] dropped from [old]/5 to [new]/5."]
    [Retrying... / All categories now >= THRESHOLD.]
    ```
11. **Interactive mode only** (`--interactive` flag): Before starting the next automatic retry, offer the user an early exit via `AskUserQuestion`. If `--interactive` is not set, proceed directly to the next retry without prompting.

**If any score < THRESHOLD AND iteration >= MAX_RETRIES** (user decision):

Use `AskUserQuestion` with the current scores and prompt analysis context. Build options dynamically:

```
Quality scores still below [THRESHOLD] after [MAX_RETRIES] automatic fix attempts.

Current scores (actual state of codebase):
- [Category]: [CURRENT_SCORES[category]]/5
- ...

Best achieved across all iterations:
- [Category]: [BEST_SCORES[category]]/5 [if different from current: "(current: [CURRENT_SCORES[category]]/5)"]
- ...

Prompt verdict: [PROMPT_VERDICT]
[If WEAK/POOR: "Prompt quality may be contributing to low scores. A suggested improved prompt is available in the report."]
```

Options (build dynamically):
1. Always: "Retry again (2 more automatic attempts on failing categories)"
2. Only if `PROMPT_VERDICT` is WEAK or POOR: "Retry with improved prompt (use suggested rewrite)"
3. If multiple categories are failing: "Select specific categories to retry"
4. Always: "Accept current quality and finalize"

If user chooses option 1, reset the retry counter to 0 and repeat with `MAX_RETRIES` more automatic attempts. If user chooses option 2, use `SUGGESTED_PROMPT` as the task description for the next fix pass and reset retry counter. If user chooses option 3, prompt the user to select which failing categories to fix, then retry only those. If user chooses option 4 (accept), proceed to Step 6.

## Step 6: Final Report

**Write the consolidated report** to `REPORT_PATH`. This is a single structured file reflecting the final state. The iterations log (`ITERATIONS_PATH`) is preserved as a separate file for audit purposes.

The report structure:
1. Header with final verdict and final scores (using `CURRENT_SCORES` — the actual state of the codebase)
2. If any `BEST_SCORES` differ from `CURRENT_SCORES`, note regressions: "Best achieved: X/5 (current: Y/5 — regressed in iteration N)"
3. Agent checklist results
4. Findings (Strengths, Issues, Security)
5. Prompt Analysis (if triggered)
6. Iteration History (condensed — one subsection per iteration with score deltas, not full re-listings)
7. Recommendations

Use `TaskUpdate` to update task status based on final verdict (computed from `CURRENT_SCORES`):

- **EXCELLENT / PASS**: mark task completed
- **CONDITIONAL PASS**: mark completed, create follow-up task for improvements
- **FAIL**: keep task in current status with feedback

**Clean up**: Delete the state file (`STATE_PATH`) after writing the final report — it is no longer needed.

**Output a summary to the user** after writing the report:
```
Evaluation complete.
Verdict: [FINAL_VERDICT] | Iterations: [COUNT]
Scores: Completeness [X]/5, Groundedness [X]/5, Technical Quality [X]/5, Agent Compliance [X]/5, User Value [X]/5 (avg [X.X]/5)
[If any BEST_SCORES != CURRENT_SCORES: "Note: [Category] regressed during fix passes — best achieved was [X]/5, current is [Y]/5."]
[If CONDITIONAL PASS: "Follow-up task created for remaining improvements."]
Report: [REPORT_PATH]
Iteration log: [ITERATIONS_PATH]
```

## Report Template

```markdown
# Evaluation Report

**Task**: [task description]
**Agent**: [agent type]
**Date**: [timestamp]
**Iterations**: [count]
**Final Verdict**: [EXCELLENT / PASS / CONDITIONAL PASS / FAIL]

## Scores

| Category           | Score | Best Achieved | Notes                    |
|--------------------|-------|---------------|--------------------------|
| Completeness       | X/5   | X/5           | [brief explanation]      |
| Groundedness       | X/5   | X/5           | [brief explanation]      |
| Technical Quality  | X/5   | X/5           | [brief explanation]      |
| Agent Compliance   | X/5   | X/5           | [brief explanation]      |
| User Value         | X/5   | X/5           | [brief explanation]      |
| **Average**        | X.X/5 |               |                          |

_Score column reflects actual codebase state. Best Achieved column shows highest score reached across iterations (differs only if regression occurred)._

## Agent Checklist

[Each checklist item with pass/fail status and brief note]

## Findings

### Strengths
- [what was done well]

### Issues
- [problems found with severity]

### Security
- [any security concerns]

## Prompt Analysis

_Omit this entire section if all output scores >= THRESHOLD (prompt evaluation was not triggered)._

**Original Prompt**: [the user's original task description]
**Prompt Verdict**: [STRONG / ADEQUATE / WEAK / POOR]

| Dimension      | Score | Notes                    |
|----------------|-------|--------------------------|
| Specificity    | X/5   | [brief explanation]      |
| Context        | X/5   | [brief explanation]      |
| Constraints    | X/5   | [brief explanation]      |
| Actionability  | X/5   | [brief explanation]      |
| Scope          | X/5   | [brief explanation]      |

**Examples Recommended**: [Yes/No] — [reason based on output evaluation results]

### Suggested Improved Prompt
_Include only when prompt verdict is WEAK or POOR._

[Rewritten prompt addressing failing dimensions.]

## Iteration History

### Iteration 0 (Initial)
| Category | Score |
|----------|-------|
| ... | X/5 |
Verdict: [verdict]

### Iteration N (Fix Pass)
| Category | Previous | New | Delta |
|----------|----------|-----|-------|
| [only changed categories] | X/5 | Y/5 | +/-Z |
[If regression: "Warning: Regression detected in [Category]"]
Verdict: [verdict]

## Recommendations
- [specific output improvements]
- [specific prompt improvements for future tasks]

<!-- SCORES:{"completeness":N,"groundedness":N,"technical_quality":N,"agent_compliance":N,"user_value":N} -->
```

## Arguments

- `/evaluate-and-improve` — evaluate most recently completed task
- `/evaluate-and-improve latest` — evaluate most recently completed task
- `/evaluate-and-improve 42` — evaluate task with ID 42
- `/evaluate-and-improve python-dev` — evaluate most recent work by the python-dev agent
- `/evaluate-and-improve software-architect` — evaluate most recent work by the software-architect agent
- `/evaluate-and-improve "add auth"` — search for a task matching "add auth"
- `/evaluate-and-improve --threshold=4` — use stricter quality threshold (score < 4 triggers retry)
- `/evaluate-and-improve --retries=1` — limit to 1 automatic retry before asking user
- `/evaluate-and-improve --retries=0` — evaluate only, no automatic fix passes
- `/evaluate-and-improve --interactive` — prompt for confirmation before each automatic retry
- `/evaluate-and-improve 42 --threshold=4 --retries=3` — combine task selection with overrides

**Parsing precedence**: Flags (`--threshold`, `--retries`, `--interactive`) are extracted first. Then: `latest` keyword -> numeric task ID -> known agent name -> substring search.

**Validation**: `--threshold` must be 1-5, `--retries` must be 0-10. Invalid values trigger a warning and fall back to defaults.

## References

- **Quality rubric and agent checklists**: See `references/quality-rubric.md` for full scoring dimensions, agent-specific checklists, and verdict criteria
- **Score parsing script**: See `scripts/parse_scores.sh` for deterministic score extraction from report files
