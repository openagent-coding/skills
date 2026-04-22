# OpenAgent Coding Skills

A collection of Claude Code skills for AI-assisted software engineering workflows. Each skill extends Claude Code with specialized capabilities -- from codebase analysis and PR review to session telemetry and stock research.

## Skills

### Directory-based skills (with full README)

| Skill | Description | README |
|-------|-------------|--------|
| [code-tree](code-tree/) | Build and query a knowledge graph of any codebase with call graph, test mapping, and impact analysis | [code-tree/README.md](code-tree/README.md) |
| [context-auto-summarizer](context-auto-summarizer/) | Automatic context window management with intelligent affinity-based summarization | [context-auto-summarizer/README.md](context-auto-summarizer/README.md) |
| [evaluate-and-improve](evaluate-and-improve/) | Evaluate agent outputs against quality standards and auto-retry targeted fixes on failing categories | [evaluate-and-improve/README.md](evaluate-and-improve/README.md) |
| [financial-stock-analyzer](financial-stock-analyzer/) | Multi-dimensional stock analysis with buy/sell/hold recommendations based on six research dimensions | [financial-stock-analyzer/README.md](financial-stock-analyzer/README.md) |
| [pr-review](pr-review/) | Structured PR review with parallel sub-agents for impact analysis, code quality, and GitHub commenting | [pr-review/README.md](pr-review/README.md) |
| [session-metrics-tracker](session-metrics-tracker/) | Silent background telemetry tracking context usage, LLM calls, and human interrupts with CSV/plot reports | [session-metrics-tracker/README.md](session-metrics-tracker/README.md) |

### Standalone skills

| Skill | Description |
|-------|-------------|
| [explain-code](explain-code.md) | Explains code using analogies, ASCII diagrams, step-by-step walkthroughs, and common gotchas |
| [multi-agent-coordinator](multi-agent-coordinator.md) | Orchestrates parallel task execution by mapping tasks to specialized agents (python-dev, go-developer, devops, tech-writer, etc.) based on keyword analysis and dependency ordering |
| [output-evaluator](output-evaluator.md) | Evaluates agent outputs with a 5-dimension quality scoring rubric (Completeness, Groundedness, Technical Quality, Agent Compliance, User Value) and generates detailed evaluation reports |
| [pr-summary](pr-summary.md) | Concise pull request summarization using PR diff and comments |

## Installation

These skills are designed for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). To use a skill:

1. Clone this repository
2. Reference the skill directory (or `.md` file) in your Claude Code configuration
3. Some skills require hooks in `.claude/settings.json` -- see each skill's README for setup details

## License

[MIT](LICENSE)
