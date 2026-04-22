# PR Review

Structured pull request review with parallel sub-agents for impact analysis, code quality assessment, and optional GitHub commenting.

## Overview

Reviews GitHub pull requests by grouping changed files into functional areas, launching parallel sub-agents for impact and code quality analysis, deduplicating findings, and optionally posting inline comments with user approval.

## Operating Modes

| Mode | Behavior |
|------|----------|
| `analysis-only` (default) | Analyze and report findings in chat |
| `suggested-comments` | Draft inline comment payloads without posting |
| `post-comments` | Post comments to GitHub after explicit user approval |

## Workflow

1. **Preflight** -- verify GitHub auth, repo context, PR state
2. **Fetch** -- PR metadata, diff, changed files, HEAD SHA
3. **Explore** -- understand repo structure, languages, frameworks, guidelines
4. **Group** -- categorize changed files by functional area with size guardrails
5. **Review** -- launch parallel sub-agents per group:
   - **Impact Assessment** -- breaking changes, cross-module impact, security surface
   - **Code Quality** -- bugs, performance, duplication, error handling, security
   - **Draft Comments** (optional) -- inline comment payloads with confidence scoring
6. **Aggregate** -- merge and deduplicate findings, enforce comment caps by PR size
7. **Approve** -- show findings to user, ask before any GitHub write action
8. **Post** -- submit comments only if approved

## PR Size Guardrails

| Size | Threshold | Comment Cap |
|------|-----------|-------------|
| Small | <= 15 files, <= 600 lines | 20 inline comments |
| Medium | 16-40 files or 601-2000 lines | 12 inline comments |
| Large | > 40 files or > 2000 lines | 8 inline comments |

## Usage

```
/pr-review 123           # Review PR #123
/pr-review <PR_URL>      # Review PR by URL
```

## References

- [Review checklist](references/review-checklist.md)
- [GitHub comment format](references/github-comment-format.md)