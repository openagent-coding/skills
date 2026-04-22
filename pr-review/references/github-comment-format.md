# GitHub PR Comment Formats

## Inline Review Comments

Use `gh api` to post inline comments on specific files and lines in a PR.

### Single Inline Comment

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="**[SEVERITY]** Description of issue

Suggestion: how to fix it" \
  -f commit_id="{HEAD_SHA}" \
  -f path="{file_path}" \
  -f line={line_number} \
  -f side="RIGHT"
```

### Multi-line Comment

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="**[SEVERITY]** Description" \
  -f commit_id="{HEAD_SHA}" \
  -f path="{file_path}" \
  -f start_line={start_line} \
  -f line={end_line} \
  -f start_side="RIGHT" \
  -f side="RIGHT"
```

### PR-level Summary Comment

```bash
gh pr comment {pr_number} --body "$(cat <<'EOF'
### PR Review Summary

**Scope**: X files reviewed across Y functional groups

#### Critical Issues (N found)
- `file:line` - Description

#### Important Issues (N found)
- `file:line` - Description

#### Suggestions (N found)
- `file:line` - Description

#### Impact Assessment
- **Risk Level**: Low/Medium/High
- **Breaking Changes**: Yes/No
- **Test Coverage**: Adequate/Gaps identified

Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

## Getting PR Details

```bash
# PR metadata (title, description, state, author)
gh pr view {pr_number} --json title,body,state,author,labels,reviewDecision

# Changed files list
gh pr diff {pr_number} --name-only

# Full diff
gh pr diff {pr_number}

# PR comments and review comments
gh pr view {pr_number} --comments
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments

# Get HEAD commit SHA (needed for inline comments)
gh pr view {pr_number} --json headRefOid -q '.headRefOid'
```

## Severity Labels

Use in comment body prefix:
- **[CRITICAL]** - Must fix before merge (bugs, security, data loss)
- **[IMPORTANT]** - Should fix (performance, error handling, logic)
- **[SUGGESTION]** - Nice to have (style, clarity, minor optimization)
- **[POSITIVE]** - Good pattern worth noting