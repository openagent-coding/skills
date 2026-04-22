# Knowledge Graph Schema

## Output Files

### graph.json

Full knowledge graph with nodes, edges, and metadata including file hashes and module boundaries.

```json
{
  "metadata": {
    "repo_root": "/abs/path",
    "generated_at": "ISO-8601",
    "languages": {"python": 42, "go": 38},
    "total_files": 80,
    "total_symbols": 500,
    "symbol_types": {"class": 50, "function": 200, "method": 250},
    "edge_types": {"contains": 500, "imports": 120, "calls": 300, "inherits": 20, "tests": 40},
    "file_hashes": {"src/main.py": "sha256hex...", "...": "..."},
    "module_boundaries": [
      {"root_dir": "", "build_file": "pyproject.toml", "name": "my-project", "language": "python"},
      {"root_dir": "services/api", "build_file": "go.mod", "name": "github.com/org/api", "language": "go"}
    ]
  },
  "nodes": [...],
  "edges": [...]
}
```

**Node types:**

| Type | ID Format | Fields |
|------|-----------|--------|
| file | `file:<rel_path>` | name, path, language, line_count, is_test |
| class | `class:<file>:<name>` | name, file, line_start, line_end, bases, decorators, docstring, is_test |
| function | `function:<file>:<name>` | name, file, line_start, line_end, params, signature, docstring, is_test |
| method | `method:<file>:<class>.<name>` | name, file, line_start, line_end, scope, params, signature, is_test |
| struct | `struct:<file>:<name>` | name, file, line_start, line_end |
| interface | `interface:<file>:<name>` | name, file, line_start, line_end |
| enum | `enum:<file>:<name>` | name, file, line_start, line_end |
| constant | `constant:<file>:<name>` | name, file, line_start, line_end |

**Common node fields:**

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (see ID Convention below) |
| type | string | Node type (file, class, function, method, etc.) |
| name | string | Symbol name |
| file | string | Relative file path |
| language | string | Programming language |
| line_start | int | Starting line number |
| line_end | int | Ending line number |
| scope | string | Parent scope (e.g., class name for methods) |
| params | list | Parameter names |
| bases | list | Base classes/interfaces |
| decorators | list | Decorator names (Python) |
| docstring | string | First 200 chars of documentation |
| signature | string | Function signature with type annotations |
| exported | bool | Whether the symbol is public |
| is_test | bool | Whether this is a test file/symbol |

**Edge types:**

| Type | Meaning | Source -> Target | Metadata |
|------|---------|-----------------|----------|
| contains | Parent contains child | file -> class, class -> method | - |
| imports | File imports module/file | file -> file, file -> module, file -> symbol | `{from_import: true}` for `from X import Y` |
| inherits | Class extends another | class -> class | `{unresolved: true}` if base not found in codebase |
| calls | Function/method calls another | function -> function, method -> method | `{line: N}` line of the call site |
| tests | Test covers source code | test_file -> source_file, test_func -> func | `{strategy: "path_mirror"|"import"|"name_match"}` |

### tags.json

Flat symbol index sorted by file and line number.

```json
[
  {
    "name": "MyClass",
    "type": "class",
    "file": "src/models.py",
    "line": 15,
    "end_line": 85,
    "language": "python",
    "bases": ["BaseModel"],
    "doc": "My class docstring...",
    "signature": null,
    "is_test": false
  },
  {
    "name": "process_data",
    "type": "function",
    "file": "src/pipeline.py",
    "line": 42,
    "end_line": 67,
    "language": "python",
    "params": ["input_data", "config"],
    "signature": "(input_data: dict, config: Config) -> Result",
    "doc": "Process incoming data..."
  }
]
```

**Tag fields:**

| Field | Always present | Description |
|-------|---------------|-------------|
| name | yes | Symbol name |
| type | yes | Symbol type |
| file | yes | Relative file path |
| line | yes | Start line number |
| end_line | yes | End line number |
| language | yes | Programming language |
| scope | if applicable | Parent scope (class name for methods) |
| params | if applicable | Parameter names |
| bases | if applicable | Base classes |
| doc | if present | Docstring (truncated to 200 chars) |
| signature | if present | Full function signature |
| private | if true | Symbol is private (starts with `_`) |
| is_test | if true | Symbol is in a test file or is a test function |

### modules.json

Directory-level dependency map with build module boundaries and test coverage.

```json
{
  "modules": {
    "src/api": {
      "files": ["src/api/server.py", "src/api/routes.py"],
      "depends_on": ["src/models", "src/utils"],
      "tested_by": ["tests/api"]
    },
    "src/models": {
      "files": ["src/models/user.py", "src/models/base.py"],
      "depends_on": ["src/utils"],
      "tested_by": ["tests/models"]
    }
  },
  "build_modules": [
    {"root_dir": "", "build_file": "pyproject.toml", "name": "my-project", "language": "python"},
    {"root_dir": "services/api", "build_file": "go.mod", "name": "github.com/org/api", "language": "go"}
  ]
}
```

**Build file detection:**

| Build File | Language | Extracted Info |
|------------|----------|----------------|
| go.mod | Go | Module path (used for import prefix stripping) |
| package.json | JavaScript | Package name |
| pyproject.toml | Python | Project name |
| setup.py / setup.cfg | Python | Project name |
| Cargo.toml | Rust | Crate name |
| pom.xml | Java | Artifact ID |
| build.gradle(.kts) | Java | - |
| Gemfile | Ruby | - |
| composer.json | PHP | - |
| pubspec.yaml | Dart | - |
| mix.exs | Elixir | - |

### summary.md

Human/AI-readable overview containing:
- Statistics (files, symbols, languages, edge type breakdown)
- Directory structure with per-directory stats (including test file counts)
- Hub files (most imported)
- Most-called symbols
- Key types table
- Inheritance hierarchy (text-based tree)
- Key functions table
- Module dependency map
- Test coverage map (which source files are tested by which test files)

## ID Convention

All node IDs follow: `<type>:<file_path>:<qualified_name>`

- Functions: `function:src/utils.py:process_data`
- Methods: `method:src/models.py:User.save`
- Nested: `method:src/models.py:User.Meta.get_fields` (nested class methods use dot-separated qualified names)
- Unresolved references use `?` for file: `class:?:BaseModel`

## Incremental Updates

When `--incremental` is used, `code_tree.py` compares SHA-256 file hashes stored in `graph.json` metadata against current files. Only changed files are re-parsed. The `file_hashes` field in metadata stores the mapping from relative path to hash.

## Test Detection

Files are classified as test files based on path markers:
- `test_`, `_test.`, `.test.`, `.spec.`, `tests/`, `__tests__/`, `test/`

Test-to-source mapping uses three strategies (in order):
1. **Path mirroring**: `test_foo.py` -> `foo.py`, `tests/test_bar.py` -> `src/bar.py`
2. **Import analysis**: Test file imports source file directly
3. **Name matching**: `test_process` -> `process`, `TestUser` -> `User`
