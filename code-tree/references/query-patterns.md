# Query Patterns for AI Agents

## Using the Knowledge Graph

### Quick Start: Read summary.md First

Always start with `docs/code-tree/summary.md` for a codebase overview. Then use
`query_graph.py` or read `graph.json`/`tags.json` directly for specifics.

### Common Workflows

**"How does feature X work?"**
1. `query_graph.py --search "X"` to find relevant symbols
2. `query_graph.py --deps <file>` to trace dependencies (imports, inheritance, cross-file calls)
3. `query_graph.py --callers <symbol>` to see who uses it
4. `query_graph.py --callees <symbol>` to see what it calls
5. `query_graph.py --chunks <file>` to extract code snippets for context

**"What depends on this file?"**
1. `query_graph.py --rdeps path/to/file.py`

**"What is the full impact of changing this file?"**
1. `query_graph.py --impact path/to/file.py` — transitive impact via imports, calls, and inheritance
2. `query_graph.py --impact path/to/file.py --depth 8` — deeper traversal

**"Which tests do I need to run after this change?"**
1. `query_graph.py --test-impact path/to/file.py` — finds all affected test files
2. `query_graph.py --test-coverage path/to/file.py` — shows which tests directly cover a file

**"What calls this function?"**
1. `query_graph.py --callers function_name`

**"What does this function call?"**
1. `query_graph.py --callees function_name`

**"How does function A reach function B?"**
1. `query_graph.py --call-chain function_a function_b`
2. `query_graph.py --call-chain function_a function_b --depth 10` — search deeper

**"Show me the class hierarchy"**
1. `query_graph.py --hierarchy ClassName`

**"What are the main entry points?"**
1. `query_graph.py --entry-points`

**"Give me an overview of this module"**
1. `query_graph.py --module src/api` — includes files, dependencies, test coverage, and symbols

### Impact Analysis for Code Reviews

When reviewing a PR that changes `src/models/user.py`:

```bash
# Step 1: What is affected?
python query_graph.py --impact src/models/user.py

# Step 2: Which tests need to run?
python query_graph.py --test-impact src/models/user.py

# Step 3: Who calls functions in this file?
python query_graph.py --callers UserModel

# Step 4: What does this file depend on?
python query_graph.py --deps src/models/user.py
```

### Direct JSON Queries

For programmatic access, use `--json` flag with any query:
```bash
python query_graph.py --search "auth" --json | python -m json.tool
python query_graph.py --impact src/api/auth.py --json
python query_graph.py --test-impact src/api/auth.py --json
```

### Reading graph.json Directly

Use `jq` for quick lookups:
```bash
# Find all classes
jq '.nodes[] | select(.type == "class") | {name, file, line_start}' graph.json

# Find import edges for a file
jq '.edges[] | select(.source == "file:src/main.py" and .type == "imports")' graph.json

# Find most-imported files
jq '[.edges[] | select(.type == "imports" and (.target | startswith("file:")))] | group_by(.target) | map({file: .[0].target, count: length}) | sort_by(-.count) | .[0:10]' graph.json

# Find most-called symbols
jq '[.edges[] | select(.type == "calls")] | group_by(.target) | map({symbol: .[0].target, callers: length}) | sort_by(-.callers) | .[0:10]' graph.json

# Find all call edges from a specific function
jq '.edges[] | select(.source | startswith("function:src/pipeline.py:process")) | select(.type == "calls")' graph.json

# Find all test edges (test-to-source mappings)
jq '.edges[] | select(.type == "tests")' graph.json

# Find test files for a source file
jq '.edges[] | select(.type == "tests" and .target == "file:src/models/user.py")' graph.json

# Find all symbols marked as tests
jq '.nodes[] | select(.is_test == true) | {name, type, file}' graph.json

# Find build module boundaries
jq '.metadata.module_boundaries' graph.json
```

### Using tags.json for Symbol Lookup

```bash
# Find all definitions of "Pipeline"
jq '.[] | select(.name == "Pipeline")' tags.json

# Find all exported functions in a directory
jq '.[] | select(.type == "function" and (.file | startswith("sdk/")) and (.private != true))' tags.json

# Find all test functions
jq '.[] | select(.is_test == true and .type == "function")' tags.json

# Find functions with signatures
jq '.[] | select(.signature != null) | {name, file, signature}' tags.json

# Find all classes that extend a specific base
jq '.[] | select(.type == "class" and (.bases // [] | any(. == "BaseModel")))' tags.json
```

### Using modules.json for Module Analysis

```bash
# Find all modules and their dependencies
jq '.modules | to_entries[] | {module: .key, depends_on: .value.depends_on}' modules.json

# Find modules with test coverage
jq '.modules | to_entries[] | select(.value.tested_by) | {module: .key, tested_by: .value.tested_by}' modules.json

# List build module boundaries
jq '.build_modules' modules.json
```

## Regenerating the Graph

Re-run when codebase changes significantly:
```bash
python scripts/code_tree.py --repo-root /path/to/repo
```

For faster updates after small changes:
```bash
python scripts/code_tree.py --repo-root /path/to/repo --incremental
```

Options:
- `--exclude-tests` - Exclude test files
- `--exclude PATTERN` - Exclude additional patterns
- `--no-tree-sitter` - Force regex-only parsing
- `--no-call-graph` - Skip call graph (faster)
- `--incremental` - Only reparse changed files
- `--quiet` - Suppress progress output
