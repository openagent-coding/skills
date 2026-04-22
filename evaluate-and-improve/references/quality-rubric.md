# Quality Rubric

## Table of Contents
- [Scoring Dimensions](#scoring-dimensions)
- [Agent-Specific Checklists](#agent-specific-checklists)
- [Verdict Criteria](#verdict-criteria)
- [Prompt Evaluation](#prompt-evaluation)

## Scoring Dimensions

Rate each dimension 1-5:

### Completeness
- 1: Major requirements missing
- 2: Several requirements missing
- 3: Most requirements met
- 4: All requirements met with minor gaps
- 5: All requirements fully addressed

### Groundedness
- 1: Major deviation from requested context
- 2: Significant misalignment
- 3: Mostly aligns with context/prompt
- 4: Strong alignment with minor drift
- 5: Everything matches as requested

### Technical Quality
- 1: Poor quality, many issues
- 2: Below average, significant issues
- 3: Acceptable quality, some issues
- 4: Good quality, minor issues
- 5: Excellent quality, best practices followed

### Agent Compliance
- 1: Major deviations from agent standards
- 2: Several standards not followed
- 3: Most standards followed
- 4: Strong compliance with minor gaps
- 5: Exemplary adherence to all standards

### User Value
- 1: Not usable by user
- 2: Requires significant rework
- 3: Usable with modifications
- 4: Ready to use with polish
- 5: Ready to use, exceeds expectations

## Agent-Specific Checklists

### Python Development (python-dev)
- Type hints on all functions and classes
- PEP 8 compliance (formatting, naming)
- Proper exception handling with specific exceptions
- Clear docstrings following PEP 257
- Edge cases handled appropriately
- Security considerations (no hardcoded secrets, input validation)
- Performance implications considered
- Testing strategy included

### Go Development (go-developer)
- Idiomatic Go code patterns
- Comprehensive error handling (no panic in library code)
- Race condition safety (proper goroutine/channel usage)
- Memory leak prevention
- Clear documentation comments
- Tests and benchmarks included
- golangci-lint compliance

### DevOps (devops)
- Security hardening applied
- Secrets properly managed (no plaintext passwords)
- Resource limits and requests set
- Monitoring and logging configured
- Backup and recovery procedures planned
- Cost optimization considered
- Complete documentation provided

### Documentation (tech-writer)
- Clear structure and navigation
- Accurate technical information
- Consistent formatting and style
- Appropriate examples included
- Target audience appropriately addressed
- Links and references valid
- Grammar and spelling correct

### Code Analysis (code-analyzer)
- Architecture assessment thorough
- Security vulnerabilities identified
- Performance bottlenecks analyzed
- Code quality metrics provided
- Best practices compliance verified
- Maintainability factors evaluated
- Technical debt documented

### Testing (test-planner)
- Test scope clearly defined
- Test levels identified (unit/integration/e2e)
- Test cases documented with clear steps
- Edge cases and error conditions covered
- Performance testing criteria included
- Security testing considerations
- Automation strategy defined

### Software Architecture (software-architect)
- Architecture decisions justified with trade-offs
- Component boundaries clearly defined
- Scalability considerations documented
- Non-functional requirements addressed (performance, reliability, security)
- Integration points and interfaces identified
- Migration and rollback strategy included where applicable
- Diagrams or visual aids provided where appropriate
- Technology choices aligned with project constraints

### General Purpose (general-purpose)
- Requirements addressed as specified
- Code is functional and free of obvious bugs
- No hardcoded secrets or credentials
- Consistent coding style within the output
- Error handling present for external inputs
- Output is well-organized and readable
- No unnecessary complexity or dead code

## Verdict Criteria

Evaluate top-down; the first matching rule applies:

- **EXCELLENT**: All scores >= 4 AND average >= 4.5
- **PASS**: All scores >= 3 AND average >= 3.5
- **CONDITIONAL PASS**: All scores >= 2 AND average >= 2.5
- **FAIL**: Any score < 2 OR average < 2.5

## Prompt Evaluation

Run this analysis when any output score is below the configured THRESHOLD (see SKILL.md for the active threshold — default 3). Evaluate the original user prompt/task description against these 5 dimensions (each scored 1-5):

### Specificity
- 1: Vague, no concrete requirements ("make it better")
- 2: General direction but missing details ("add authentication")
- 3: Clear goal with some requirements specified
- 4: Well-defined requirements with acceptance criteria
- 5: Precise requirements, edge cases called out, success criteria explicit

### Context
- 1: No background or context provided
- 2: Minimal context, agent must guess domain/codebase details
- 3: Sufficient context for the core task
- 4: Good context including relevant files, architecture, constraints
- 5: Comprehensive context with dependencies, history, and rationale

### Constraints
- 1: No constraints or boundaries defined
- 2: Implicit constraints only (agent must infer)
- 3: Key constraints stated (language, framework, style)
- 4: Clear constraints with priorities and trade-offs noted
- 5: Full constraints including performance targets, compatibility, and non-goals

### Actionability
- 1: Agent cannot act without significant clarification
- 2: Agent must make major assumptions to proceed
- 3: Agent can proceed with minor assumptions
- 4: Agent can act directly with minimal interpretation
- 5: Unambiguous — single clear interpretation, ready to execute

### Scope
- 1: Scope undefined or impossibly broad for one agent
- 2: Scope too large, should be decomposed into subtasks
- 3: Scope is reasonable but boundaries are unclear
- 4: Well-scoped with clear boundaries
- 5: Precisely scoped, decomposed if needed, dependencies identified

### Conditional: Examples Recommendation

Do NOT score this as a standalone dimension. Instead, after completing the output evaluation, determine whether providing examples would have materially improved the results:

**Recommend examples when ANY of these are true:**
- Groundedness scored < 3 (output drifted from intent — examples anchor expectations)
- Agent Compliance scored < 3 AND the prompt didn't specify coding style/patterns
- Completeness scored < 3 AND the requirements were ambiguous (examples clarify scope)
- The task involves generating a specific output format (API response, report, config file)

**Do NOT recommend examples when:**
- The failure was purely technical (bugs, missing error handling) not interpretive
- The prompt was already specific enough (Specificity >= 4)
- The task is a clear fix/patch with obvious expected behavior

### Prompt Verdict

- **STRONG**: All prompt scores >= 4, average >= 4.0 — prompt quality is not a factor
- **ADEQUATE**: All prompt scores >= 3, average >= 3.0 — prompt is workable, minor improvements possible
- **WEAK**: Any prompt score < 3 — prompt likely contributed to low output quality, improvements recommended
- **POOR**: Any prompt score < 2 or average < 2.0 — prompt needs significant rework before retry

### Improved Prompt Template

When prompt verdict is WEAK or POOR, generate a rewritten prompt that addresses every failing dimension. Structure:

```
## Suggested Improved Prompt

[Rewritten version of the original prompt that:]
- Adds missing specificity (concrete requirements, success criteria)
- Provides missing context (relevant files, architecture, domain)
- States constraints explicitly (language, framework, style, performance)
- Removes ambiguity (single clear interpretation)
- Right-sizes scope (decompose if too broad)
- [If examples recommended] Includes example of expected output
```
