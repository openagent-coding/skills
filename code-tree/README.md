# Code Tree

Build and query a knowledge graph of any codebase with call graph, test mapping, and impact analysis.

## Overview

Code Tree uses a hybrid **Parse + Index + Retrieve** approach to analyze codebases. It extracts symbols (classes, functions, methods, imports), maps call dependencies, links tests to source code, detects module boundaries, and generates structured artifacts for AI agent consumption.

## When to Use

- Understanding a new codebase or generating architecture overviews
- Tracing dependencies between modules or files
- Finding symbol definitions and call chains
- Assessing change impact ("what breaks if I change X?")
- Finding which tests to run after a change
- Analyzing inheritance hierarchies or finding entry points

## How It Works

### 1. Generate the Knowledge Graph

```bash
python scripts/code_tree.py --repo-root /path/to/repo
```

Outputs to `<repo-root>/docs/code-tree/`:

| File | Contents |
|------|----------|
| `graph.json` | Full knowledge graph (nodes + edges, call graph, test mapping) |
| `tags.json` | Flat symbol index for quick lookup |
| `modules.json` | Module-level dependency map |
| `summary.md` | Human/AI-readable codebase overview |

### 2. Query the Graph

```bash
python scripts/query_graph.py --symbol ClassName       # Find a symbol
python scripts/query_graph.py --deps path/to/file.py   # File dependencies
python scripts/query_graph.py --callers func_name       # Who calls this?
python scripts/query_graph.py --impact path/to/file.py  # Change impact analysis
python scripts/query_graph.py --test-impact path/to/file.py  # Affected tests
```

Add `--json` for machine-readable output. Use `--depth N` to control traversal depth.

## Supported Languages

| Language | Primary Parser | Fallback |
|----------|---------------|----------|
| Python | `ast` (built-in) | - |
| Go, JS/TS, Java, Rust, C#, Protobuf | tree-sitter | Regex |
| Other | - | Regex |

Zero external dependencies required. Install `tree-sitter` for enhanced parsing.

## References

- [Graph schema](references/graph-schema.md) -- node/edge types, ID conventions, output formats
- [Query patterns](references/query-patterns.md) -- common workflows, impact analysis patterns, jq recipes