---
name: code-tree
description: >
  Build and query a knowledge graph of any codebase with call graph,
  test mapping, and impact analysis. Uses a hybrid Parser + Knowledge
  Graph + Chunked Context approach. Extracts symbols (classes, functions,
  methods, imports), maps call dependencies, links tests to source code,
  detects module boundaries, and generates structured artifacts for AI
  agent consumption. Use when: (1) Understanding a new codebase,
  (2) Tracing dependencies between modules/files, (3) Finding symbol
  definitions and call chains, (4) Generating codebase architecture
  overviews, (5) Assessing change impact ("what breaks if I change X?"),
  (6) Finding which tests to run after a change, (7) Analyzing
  inheritance hierarchies, (8) Finding entry points, or (9) Any code
  analysis question. Triggers on requests like "analyze the codebase",
  "show me the dependency graph", "map this repository", "what calls
  this function", "what is the impact of changing this file", "which
  tests do I need to run", "trace the data flow", "generate code tree",
  "find all classes", etc.
---

# Code Tree

Hybrid codebase analysis: Parse (Tree-sitter/AST) -> Index (Knowledge Graph) -> Retrieve (Chunked Context).

## Workflow

### 1. Generate the Knowledge Graph

Run the parser to scan the entire codebase:

```bash
python <skill-dir>/scripts/code_tree.py --repo-root /path/to/repo
```

Output goes to `<repo-root>/docs/code-tree/`:
- `graph.json` - Full knowledge graph (nodes + edges, including call graph and test mapping)
- `tags.json` - Flat symbol index for quick lookup
- `modules.json` - Module-level dependency map with build module boundaries
- `summary.md` - Human/AI-readable codebase overview

Options:
- `--output-dir PATH` - Custom output location
- `--exclude PATTERN` - Additional exclude patterns (repeatable)
- `--exclude-tests` - Exclude test files (tests are included by default)
- `--no-tree-sitter` - Force AST/regex parsing only
- `--no-call-graph` - Skip call graph extraction (faster but less detailed)
- `--incremental` - Only reparse files that changed since last run (uses SHA-256 hashes)
- `--max-file-size N` - Skip files larger than N bytes (default: 1MB)
- `--quiet` / `-q` - Suppress progress output

### 2. Read the Summary

Start with `docs/code-tree/summary.md` for architecture overview, hub files, most-called symbols, key types, inheritance trees, test coverage map, and module dependencies.

### 3. Query the Graph

Use `query_graph.py` for targeted lookups:

```bash
# Find a symbol
python <skill-dir>/scripts/query_graph.py --symbol ClassName

# File dependencies (imports, inheritance, cross-file calls)
python <skill-dir>/scripts/query_graph.py --deps path/to/file.py

# What imports this file?
python <skill-dir>/scripts/query_graph.py --rdeps path/to/file.py

# Inheritance hierarchy
python <skill-dir>/scripts/query_graph.py --hierarchy ClassName

# Keyword search across all symbols
python <skill-dir>/scripts/query_graph.py --search "keyword"

# Module overview (with test coverage)
python <skill-dir>/scripts/query_graph.py --module src/api

# Entry points
python <skill-dir>/scripts/query_graph.py --entry-points

# Extract code chunks from a file
python <skill-dir>/scripts/query_graph.py --chunks path/to/file.py

# Who calls this function/method?
python <skill-dir>/scripts/query_graph.py --callers func_name

# What does this function call?
python <skill-dir>/scripts/query_graph.py --callees func_name

# Find call paths between two symbols
python <skill-dir>/scripts/query_graph.py --call-chain from_func to_func

# Change impact analysis (transitive)
python <skill-dir>/scripts/query_graph.py --impact path/to/file.py
python <skill-dir>/scripts/query_graph.py --impact ClassName --depth 8

# Which tests are affected by a change?
python <skill-dir>/scripts/query_graph.py --test-impact path/to/file.py

# What tests cover a file?
python <skill-dir>/scripts/query_graph.py --test-coverage path/to/file.py

# Graph statistics
python <skill-dir>/scripts/query_graph.py --stats
```

Add `--json` to any query for machine-readable output.
Set `--graph-dir` if output is not in `docs/code-tree/`.
Use `--depth N` to control impact/call-chain traversal depth (default: 5).

## Edge Types

The knowledge graph captures six relationship types:

| Edge | Meaning | Example |
|------|---------|---------|
| `contains` | Parent contains child | file -> class, class -> method |
| `imports` | File imports module/file | file -> file, file -> module |
| `inherits` | Class extends another | class -> class |
| `calls` | Function calls another | function -> function, method -> method |
| `tests` | Test covers source code | test_file -> source_file, test_func -> func |
| `type_of` | Symbol uses a type | (reserved for future use) |

## Parser Stack

Parsing uses the best available parser per language:

| Language | Primary Parser | Fallback |
|----------|---------------|----------|
| Python | `ast` module (built-in, with call graph) | - |
| Go, JS/TS, Java, Rust, C#, Protobuf | tree-sitter (if installed, with call graph) | Regex (with call graph) |
| Other languages | - | Regex |

All parsers extract symbols, imports, and call references. Call references are resolved into `calls` edges via a 4-stage resolution engine (self/this methods, same-file symbols, imports, global name match).

Zero external dependencies required. Install `tree-sitter` + grammar packages for enhanced parsing.

## References

- **Graph schema**: Read [references/graph-schema.md](references/graph-schema.md) for node/edge types, ID conventions, and output file formats
- **Query patterns**: Read [references/query-patterns.md](references/query-patterns.md) for common AI agent workflows, impact analysis patterns, jq recipes, and direct JSON access patterns
