# chadbot

A multi-agent software factory that continuously improves your product codebase -- reactively fixing what's broken and proactively building what's next.

Point chadbot at your repo, your issue tracker, and your community channels. It monitors them around the clock, triaging bugs, resolving issues, and shipping features you didn't even know your users wanted yet.

## The demo: le Chad

**le Chad** is a fictional software product that serves as chadbot's live target in this demo. It's a small, intentionally rough codebase sitting in [`le_chad/`](./le_chad/) -- think of it as the kind of early-stage product that a small team just shipped and is now struggling to maintain.

le Chad has open GitHub issues. People are complaining about it on social media. And somewhere on Hacker News, someone just posted an idea that would make it ten times better -- but the team hasn't seen it yet.

That's where chadbot comes in. Every agent in the system points at le Chad as its target: Social Recon watches for complaints about it, GitHub Triage works through its issue backlog, and Feature Builder scouts for ideas that fit its roadmap. The result is a stream of pull requests that continuously improve le Chad's codebase -- with a human always making the final call.

In a real deployment, you'd swap le Chad for your own product repo. The agents don't care what the codebase is -- they just need a repo to improve.

## How it works

chadbot runs three specialised agents in a coordinated pipeline. Each one watches a different signal source, makes decisions through Mistral-powered reasoning, and produces concrete code changes -- pull requests, patches, and feature branches -- ready for a human to review and merge.

```
  Social media          GitHub Issues          Hacker News / Community
       |                      |                          |
  ┌────▼─────┐         ┌─────▼──────┐           ┌───────▼────────┐
  │  Social   │         │   GitHub   │           │    Feature     │
  │  Recon    │         │   Triage   │           │    Builder     │
  │  Agent    │         │   Agent    │           │    Agent       │
  └────┬──────┘         └─────┬──────┘           └───────┬────────┘
       │                      │                          │
  complaints &           prioritised              new feature
  bug signals            fix plans                proposals
       │                      │                          │
       └──────────┬───────────┴──────────────────────────┘
                  │
           ┌──────▼──────┐
           │  Codebase   │
           │  Context    │     ← repo structure, vision doc, Linear tickets
           └──────┬──────┘
                  │
           ┌──────▼──────┐
           │     PR       │
           │   Pipeline   │     → branch, implement, test, open PR
           └──────┬──────┘
                  │
           human review
```

### Agent 1: Social Recon

**Reactive.** Monitors X (Twitter) for mentions, complaints, and negative sentiment about your product. When someone tweets "your app just crashed on me" or "why doesn't X support Y?", this agent catches it, extracts the underlying issue, cross-references it against known bugs, and either links it to an existing GitHub issue or creates a new one with full context.

- Watches product mentions, competitor comparisons, and frustration signals
- Classifies severity (outage vs. annoyance vs. feature request)
- Enriches issues with social proof: how many people are complaining about the same thing?

### Agent 2: GitHub Triage

**Reactive.** Scans open issues on your repo, triages them by severity, community engagement, and technical feasibility, then generates a fix plan and submits a PR. No more issues sitting open for months because nobody got around to them.

- Reads every open issue, understands the bug or request in context of the codebase
- Scores and ranks by: severity (crash > cosmetic), engagement (reactions, comments), and estimated fix effort
- Generates an implementation plan, writes the code, runs tests, and opens a draft PR
- Includes a triage summary so maintainers can review the reasoning, not just the diff

### Agent 3: Feature Builder

**Proactive.** Scans Hacker News and community forums for emerging ideas, trends, and tools that align with your product's vision. Filters noise from signal using Mistral, evaluates feasibility against your current codebase and roadmap, and builds out new features as pull requests.

- Pulls from HN front page, Show HN, and specific builder communities
- Filters by upvote threshold and AI-powered relevance scoring
- Cross-references against your existing Linear tickets and product vision to avoid duplicate work
- For the top-ranked ideas: generates a technical plan, scaffolds the implementation, and opens a feature PR

## Project structure

```
chadbot/
├── README.md
├── pyproject.toml              # Workspace root
├── .env.example                # Required API keys
│
├── feature-builder/            # Agent 3: HN idea discovery + feature PRs
│   ├── pyproject.toml
│   └── feature_builder/
│       ├── cli.py              # CLI entry point
│       └── hn.py               # HN API client + Mistral filter
│
├── social-recon/               # Agent 1: X/Twitter complaint monitoring (planned)
│
├── github-triage/              # Agent 2: Issue triage + auto-fix PRs (planned)
│
└── le_chad/                    # Demo target: the product chadbot is improving
```

## Quick start

```bash
# Clone
git clone <repo-url> && cd chadbot

# Set up environment
cp .env.example .env
# Add your MISTRAL_API_KEY to .env

# Install
uv sync

# Try the Feature Builder agent
uv run feature-builder feed show --limit 10 --min-score 5 --filter

# Search for ideas relevant to your product
uv run feature-builder search "developer tools" --min-score 20 --filter -o ideas.md
```

## Feature Builder CLI

The Feature Builder agent has a full CLI for exploring and filtering HN content:

```bash
# Browse HN feeds with upvote filtering
uv run feature-builder feed top --limit 20 --min-score 50
uv run feature-builder feed show --min-score 5 --filter

# Explore prolific builders
uv run feature-builder user shihn fogleman mholt --min-score 100 --filter

# Full-text search
uv run feature-builder search "AI agent" --min-score 20 --limit 15

# Export to markdown
uv run feature-builder feed show -s 3 -n 10 --filter -o show_ideas.md
```

**Flags:** `--limit`/`-n`, `--min-score`/`-s`, `--filter`/`-f` (Mistral AI filter), `--output`/`-o`, `--verbose`/`-v`

## Environment variables

| Variable | Used by | Description |
|----------|---------|-------------|
| `MISTRAL_API_KEY` | All agents | Mistral API key for LLM reasoning |
| `GITHUB_TOKEN` | `github-triage` | GitHub personal access token (planned) |

## Built with

- **Mistral AI** -- all LLM reasoning (filtering, triage, planning, code generation)
- **Hacker News API** -- community signal for Feature Builder
- **Python + uv** -- fast, modern Python tooling
- **httpx** -- async HTTP for API calls

## Hackathon

Built at the [Cursor Guild Hackathon](https://cursorhacklondon2026.vercel.app/) (London, April 2026).

**Track:** Road 4 -- Software Factory (Pipelines + Fleets + Continuous Improvement)

> *Systems that continuously build, test, coordinate, and improve codebases.*
