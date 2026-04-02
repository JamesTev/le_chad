# Idea Factory

Multi-agent system for discovering and validating product ideas. Each agent lives in its own package under this workspace.

## Agents

| Package | Description | Status |
|---------|-------------|--------|
| [`feature-builder`](./feature-builder/) | Scans Hacker News for product ideas using Mistral to filter signal from noise | v0.1.0 |

## Quick start

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd idea-factory

# 2. Copy the env template and add your Mistral API key
cp .env.example .env

# 3. Install all workspace packages
uv sync

# 4. Try the feature-builder CLI
uv run feature-builder feed show --limit 10 --min-score 5 --filter
```

## Project structure

```
idea-factory/
├── .env.example          # Required env vars (copy to .env)
├── pyproject.toml        # Workspace root
├── feature-builder/      # Agent: HN idea discovery
│   ├── pyproject.toml
│   ├── feature_builder/  # Python package
│   │   ├── hn.py         # HN API client + Mistral filter
│   │   └── cli.py        # CLI entry point
│   └── scripts/          # One-off test scripts
└── <your-agent>/         # Add your agent here
```

## Adding a new agent

1. Create a directory at the repo root (e.g. `my-agent/`)
2. Add a `pyproject.toml`:

```toml
[project]
name = "my-agent"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = []

[project.scripts]
my-agent = "my_agent.cli:main"
```

3. Create the Python package (`my_agent/`) inside your directory
4. Register it in the root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["feature-builder", "my-agent"]
```

5. Run `uv sync` to install everything

## Environment variables

| Variable | Required by | Description |
|----------|-------------|-------------|
| `MISTRAL_API_KEY` | `feature-builder` | Mistral API key for idea filtering |

## feature-builder usage

```bash
# Browse a HN feed
uv run feature-builder feed top --limit 20 --min-score 50

# Filter ideas with Mistral
uv run feature-builder feed show --limit 10 --min-score 5 --filter

# Explore prolific builders
uv run feature-builder user shihn fogleman mholt --min-score 50 --filter

# Search HN
uv run feature-builder search "AI agent" --min-score 20 --filter

# Save results to markdown
uv run feature-builder search "Show HN" --limit 15 --filter --output ideas.md
```

Flags: `--limit` / `-n`, `--min-score` / `-s`, `--filter` / `-f`, `--output` / `-o`, `--verbose` / `-v`
