---
name: pr-review
description: "Review GitHub pull requests with structured impact and code-quality analysis. Use when user asks to review a PR (number or URL), assess merge risk, or generate actionable review comments."
---

# PR Review

Comprehensive PR review using parallel sub-agents for impact analysis, code quality, and optional GitHub commenting.

## Operating Modes

Choose a mode before starting. Default to `analysis-only`.

- `analysis-only` (default): Analyze PR and produce findings; do not post any GitHub comments.
- `suggested-comments`: Analyze PR and draft inline comment payloads plus PR summary text; do not post.
- `post-comments`: Post inline comments and summary comment, but only after explicit user approval.

## Workflow

1. Preflight checks
2. Fetch PR details
3. Explore repo structure
4. Group changed files (with scale guardrails)
5. Launch parallel review sub-agents
6. Aggregate and deduplicate findings
7. Ask for approval before any write action
8. Post comments/summary only if approved and mode allows

### Step 1: Preflight Checks

Run these checks before reading diffs:

```bash
# Verify GitHub auth
gh auth status

# Verify repository context
gh repo view

# Resolve PR number from URL/number/current branch
gh pr view {PR_OR_BRANCH} --json number,state,isDraft,headRefOid,baseRefName,headRefName
```

If auth fails, repo is unavailable, or PR is closed/merged, stop and report the blocker.

If PR is draft:
- Continue only if user requests full review for draft PRs, otherwise provide lightweight analysis and stop.

### Step 2: Fetch PR Details

Determine the PR number from user input (number, URL, or current branch).

```bash
# Get PR metadata
gh pr view {PR_NUMBER} --json title,body,state,isDraft,author,labels,headRefOid,baseRefName,headRefName,changedFiles,additions,deletions

# Get changed files
gh pr diff {PR_NUMBER} --name-only

# Get full diff
gh pr diff {PR_NUMBER}

# Get existing comments
gh pr view {PR_NUMBER} --comments

# Get HEAD SHA (needed for inline comments)
gh pr view {PR_NUMBER} --json headRefOid -q '.headRefOid'
```

Store: PR title, description, changed file list, HEAD SHA, base branch, and size stats.

### Step 3: Explore Repo Structure

Use an exploration step (sub-agent or direct tool usage) to understand the repository:

- Read top-level files: README, AGENTS.md, CLAUDE.md, CONTRIBUTING.md, Makefile, Dockerfile, CI configs (.github/workflows/, .gitlab-ci.yml, Jenkinsfile)
- Identify project language(s), framework(s), build system
- Map module/package structure (top-level directories, their purpose)
- Identify test framework and test file patterns
- Note deployment manifests (k8s, helm, docker-compose)
- Read project guidance files in changed-file directories (e.g., AGENTS.md, CLAUDE.md, RULES.md)

Output: A brief repo context summary (language, framework, modules, test patterns, CI setup).

### Step 4: Group Changed Files (with Scale Guardrails)

Categorize the changed files into review groups. Group by functional area first, then by language if needed:

**Grouping criteria** (apply in order of priority):
1. **Functional area**: Files in the same module/package/feature directory
2. **Change type**: Source code vs tests vs config/manifests vs docs
3. **Language**: When a group spans multiple languages, split further

**Example groupings:**
- `backend/api/` - API endpoint changes (Python)
- `backend/models/` - Data model changes (Python)
- `frontend/components/` - UI component changes (TypeScript/React)
- `deploy/` - Deployment manifest changes (YAML)
- `tests/` - Test file changes (grouped with their source counterpart when possible)

Keep groups to 3-8 files each. If a group exceeds 8 files, split by subdirectory.

Apply PR-size guardrails before launching agents:

- **Small PR** (`<= 15` files and `<= 600` changed lines): Full workflow.
- **Medium PR** (`16-40` files or `601-2000` changed lines): Full workflow with stricter comment caps.
- **Large PR** (`> 40` files or `> 2000` changed lines): Run impact-first review, then ask user which areas to deep-review before posting/drafting comments.

### Step 5: Launch Parallel Review Sub-Agents

Launch analysis sub-agents per group in parallel. Avoid write actions inside sub-agents.

For each group, provide: PR title/description, repo context summary, group file list, full diff for those files, HEAD SHA, and selected operating mode.

#### Agent A: Impact Assessment

Prompt template:
```
You are reviewing a PR for impact analysis. Analyze ONLY these files: {file_list}

Context:
- PR: {title} - {description}
- Repo: {repo_context_summary}
- Base branch: {base_branch}

Tasks:
1. Read each changed file and its surrounding code to understand the change
2. Identify consumers/dependents of modified code (grep for imports/references)
3. Assess:
   - Breaking changes (API signatures, removed exports, schema changes)
   - Cross-module impact (what other parts of the codebase are affected)
   - Data flow changes (validation, serialization, queries)
   - Configuration/deployment impact
   - Security surface changes
4. Rate overall risk: Low / Medium / High with justification

Output format:
## Impact Assessment: {group_name}

### Risk Level: [Low/Medium/High]

### Breaking Changes
- [list or "None identified"]

### Cross-Module Impact
- [list affected modules/files with explanation]

### Security Considerations
- [list or "None identified"]

### Summary
[1-2 sentence summary of impact]
```

#### Agent B: Code Quality & Efficiency

Prompt template:
```
You are reviewing PR code for quality, efficiency, and correctness. Review ONLY these files: {file_list}

Context:
- PR: {title} - {description}
- Repo: {repo_context_summary}
- Project guidelines: {guidance file contents if present}

Read references/review-checklist.md for the full review checklist.

Tasks:
1. Read each changed file's diff carefully
2. Check for bugs (confidence scoring: only report >= 80)
3. Check for performance issues (N+1 queries, unbounded loops, blocking async)
4. Check for code duplication (within this PR and against existing code)
5. Check error handling (silent failures, broad catches, missing user feedback)
6. Check for security issues (injection, XSS, path traversal, secrets)
7. Verify adherence to project guidelines from AGENTS.md / CLAUDE.md / CONTRIBUTING.md (or equivalent repo guidance files)

For each issue, provide:
- File path and line number
- Severity: CRITICAL / IMPORTANT / SUGGESTION
- Confidence score (0-100)
- Description and concrete fix suggestion

Output format:
## Code Quality: {group_name}

### Critical Issues (confidence >= 90)
- `file:line` - [description] (confidence: X)

### Important Issues (confidence >= 80)
- `file:line` - [description] (confidence: X)

### Suggestions
- `file:line` - [description]

### Positive Observations
- [well-written patterns worth noting]
```

#### Agent C: Draft Inline GitHub Comments (Optional)

Prompt template:
```
You are drafting inline review comments for a GitHub PR. Analyze ONLY these files: {file_list}

Context:
- PR #{pr_number} in {owner}/{repo}
- HEAD SHA: {head_sha}
- PR: {title} - {description}

Read references/github-comment-format.md for the exact API format.

Tasks:
1. Read the diff for each file
2. Identify issues worth commenting on (only high-confidence, actionable feedback)
3. Produce candidate comment payloads (do not post):

gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="**[SEVERITY]** Description

Suggestion: concrete fix" \
  -f commit_id="{head_sha}" \
  -f path="{file_path}" \
  -f line={line_number} \
  -f side="RIGHT"

Rules:
- Only comment on issues with confidence >= 80
- Maximum 3 comments per file (prioritize by severity)
- Maximum 15 comments total across all files in this group
- Keep comments concise and actionable
- Include concrete fix suggestions
- Do NOT comment on style/formatting issues unless they violate repo guidance files
- Do NOT comment on pre-existing issues (only lines changed in this PR)
- Use severity prefixes: [CRITICAL], [IMPORTANT], [SUGGESTION]
- Return each candidate with a stable dedupe key: `{file}:{line}:{issue_type}`

Return:
- Candidate comments (payload-ready)
- Per-file summary
- Total candidate count
```

### Step 6: Aggregate and Deduplicate Findings

After all sub-agents complete:

1. Merge findings from all groups.
2. Deduplicate by `(file, line, issue_type)` and keep highest-severity variant.
3. Prioritize by severity then confidence.
4. Enforce caps:
   - Small PR: max 20 inline comments total.
   - Medium PR: max 12 inline comments total.
   - Large PR: max 8 inline comments total unless user requests expansion.
5. Exclude low-confidence or non-actionable items from inline comments.

### Step 7: Ask for Approval Before Any Write Action

Before posting anything to GitHub:

- Show user:
  - Proposed inline comments (or top N with counts)
  - Proposed PR summary comment
  - Mode currently selected
- Ask explicit confirmation:
  - "Post these comments now?"
- Only proceed if user explicitly approves.

### Step 8: Post Summary Comment (Only If Approved)

If mode is `post-comments` and user approved, post inline comments first, then post a PR-level summary comment:

```bash
gh pr comment {pr_number} --body "$(cat <<'EOF'
### PR Review Summary

**Scope**: X files reviewed across Y functional groups

#### Impact Assessment
- **Overall Risk**: [highest risk from all groups]
- **Breaking Changes**: [Yes/No - details]
- **Cross-Module Impact**: [summary]

#### Code Quality
- **Critical Issues**: N found
  - [list each with file:line]
- **Important Issues**: N found
  - [list each with file:line]
- **Suggestions**: N

#### Inline Comments
N inline comments posted across M files.

#### Recommendation
[APPROVE / REQUEST_CHANGES / COMMENT - with brief justification]

Generated by automated PR review workflow
EOF
)"
```

If mode is `analysis-only` or `suggested-comments`, do not post. Return the prepared content in the chat output.

## References

- **Review checklist**: See [references/review-checklist.md](references/review-checklist.md) for detailed review criteria, confidence scoring, and false positive filters
- **GitHub comment format**: See [references/github-comment-format.md](references/github-comment-format.md) for `gh api` commands and comment templates

## Notes

- Use `gh` CLI for all GitHub interactions, not web fetch
- Always get HEAD SHA before posting inline comments
- Respect rate limits: batch inline comments and cap comments by PR size
- If the PR is a draft, closed, or trivially simple (e.g., typo fix), skip the full review and note why
- Use repository guidance files when present (prefer AGENTS.md, then CLAUDE.md, then CONTRIBUTING.md, then .github/copilot-instructions.md)
- Run an exploration step for repo understanding before launching review agents
- Never post GitHub comments without explicit user approval in the current session