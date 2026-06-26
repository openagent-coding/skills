# OpenAgent Coding Skills

A collection of Claude Code skills for AI-assisted software engineering workflows. Each skill extends Claude Code with specialized capabilities -- from codebase analysis and PR review to session telemetry and stock research.

## Installation

This repository is a **Claude Code plugin** and can be installed via the plugin marketplace.

### Option 1: Install from marketplace (recommended)

```bash
# Register this repo as a marketplace
claude plugin marketplace add https://github.com/openagent-coding/skills.git

# Install the plugin (includes all skills)
claude plugin install openagent-coding
```

### Option 2: Install directly from git

```bash
claude plugin install --source git https://github.com/openagent-coding/skills.git
```

### Option 3: Manual installation

1. Clone this repository
2. Reference the skill directory in your Claude Code configuration
3. Some skills require hooks in `.claude/settings.json` -- see each skill's README for setup details

### Installing individual skills

To install a single skill instead of the full plugin, use the skill's subdirectory path:

```bash
claude plugin install --source git-subdir https://github.com/openagent-coding/skills.git --path <skill-name>
```

For example, to install only `kubeflow-pipelines`:

```bash
claude plugin install --source git-subdir https://github.com/openagent-coding/skills.git --path kubeflow-pipelines
```

## Skills

| Skill | Description | Docs |
|-------|-------------|------|
| [code-tree](code-tree/) | Build and query a knowledge graph of any codebase with call graph, test mapping, and impact analysis | [README](code-tree/README.md) |
| [context-auto-summarizer](context-auto-summarizer/) | Automatic context window management with intelligent affinity-based summarization | [README](context-auto-summarizer/README.md) |
| [evaluate-and-improve](evaluate-and-improve/) | Evaluate agent outputs against quality standards and auto-retry targeted fixes on failing categories | [README](evaluate-and-improve/README.md) |
| [explain-code](explain-code/) | Explains code using analogies, ASCII diagrams, step-by-step walkthroughs, and common gotchas | |
| [financial-stock-analyzer](financial-stock-analyzer/) | Multi-dimensional stock analysis with buy/sell/hold recommendations based on six research dimensions | [README](financial-stock-analyzer/README.md) |
| [kubeflow-pipelines](kubeflow-pipelines/) | Write Kubeflow Pipelines SDK v2 pipelines for OpenShift AI (RHOAI) / Data Science Pipelines | |
| [multi-agent-coordinator](multi-agent-coordinator/) | Orchestrates parallel task execution by mapping tasks to specialized agents based on keyword analysis and dependency ordering | |
| [output-evaluator](output-evaluator/) | Evaluates agent outputs with a 5-dimension quality scoring rubric and generates detailed evaluation reports | |
| [pr-review](pr-review/) | Structured PR review with parallel sub-agents for impact analysis, code quality, and GitHub commenting | [README](pr-review/README.md) |
| [pr-summary](pr-summary/) | Concise pull request summarization using PR diff and comments | |
| [session-metrics-tracker](session-metrics-tracker/) | Silent background telemetry tracking context usage, LLM calls, and human interrupts with CSV/plot reports | [README](session-metrics-tracker/README.md) |

## License

[MIT](LICENSE)
