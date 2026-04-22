# Code Review Checklist

## Impact Assessment

Evaluate each changed file for:

- **Breaking changes**: API signature changes, removed exports, schema migrations
- **Cross-module impact**: Changes that affect consumers/dependents of modified code
- **Data flow changes**: Modified input validation, serialization, database queries
- **Configuration changes**: Environment variables, feature flags, deployment manifests
- **Security surface**: New endpoints, auth changes, secrets handling, input sanitization

## Code Quality & Efficiency

### Bug Detection (confidence >= 80 only)
- Logic errors, off-by-one, null/undefined handling
- Race conditions, deadlocks, resource leaks
- Security vulnerabilities (injection, XSS, SSRF, path traversal)
- Unhandled edge cases in error paths

### Performance
- N+1 queries, missing indexes, unbounded loops
- Unnecessary allocations, missing caching opportunities
- Large payload processing without pagination/streaming
- Blocking operations in async contexts

### Duplication & Reuse
- Copy-pasted logic that should be extracted
- Reimplemented stdlib/framework functionality
- Inconsistent patterns for the same operation across files

### Error Handling
- Silent failures (empty catch blocks, swallowed errors)
- Generic catch-all without specific handling
- Missing user-facing error messages
- Fallback behavior that masks real problems

## Confidence Scoring

Rate each issue 0-100:
- **0-25**: Likely false positive or pre-existing
- **26-50**: Minor nitpick, not in project guidelines
- **51-75**: Valid but low-impact
- **76-90**: Important, requires attention
- **91-100**: Critical bug or explicit guideline violation

Only report issues with confidence >= 80.

## False Positive Filters

Skip these:
- Pre-existing issues on unchanged lines
- Things linters/typecheckers/CI will catch
- Pedantic style nitpicks not in project guidelines
- Intentional functionality changes aligned with PR purpose
- General "should have more tests" without specific gap