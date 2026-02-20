# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Imago is an AI-powered documentation coach CLI tool (alpha v0.1.0). It manages Git-based documentation repositories and uses Claude AI to review, analyze, and improve technical documentation. Built with Python 3.10+ using Hatchling as the build system.

## Development Commands

```bash
# Install for development (editable mode)
pip install -e .

# Run the CLI
imago --help

# Lint
ruff check .
ruff check . --fix    # auto-fix

# Format
ruff format .

# Run tests
pytest
pytest --cov          # with coverage
pytest tests/test_specific.py::test_name  # single test
```

## Architecture

Five modules under `src/imago/`, each with a single responsibility:

- **cli** (`cli.py`) — Typer-based command dispatch. Lazy-imports dependencies per command to keep startup fast.
- **ai** (`ai/coach.py`, `ai/prompts.py`) — Claude API integration via `anthropic` SDK. `DocumentationCoach` maintains chat history and provides review, gap analysis, quality assessment, consistency checks, and outline generation. Uses claude-sonnet-4-20250514.
- **analysis** (`analysis/indexer.py`, `analysis/validator.py`, `analysis/stats.py`) — Document scanning pipeline: SQLite FTS5 full-text search indexing, 10-check structural validation with severity levels (ERROR/WARNING/INFO), and Git-aware metrics collection (staleness, word counts).
- **git** (`git/repository.py`) — Repository management via GitPython. Auto-discovers repos by scanning the tracking directory each call (no persistent tracking file). Operations: clone, pull, push, status.
- **reports** (`reports/generator.py`) — Health report generation in Markdown or HTML. Uses a weighted scoring algorithm (base 100, capped deductions per category) with prioritized recommendations.

### Data Flow

```
CLI Command → Config (~/.imago/config.yaml) → Git Repo Operations
    → Analysis Pipeline (index → validate → stats) → AI Processing → Report/Output
```

### Key Patterns

- **Configuration**: YAML-based at `~/.imago/config.yaml` with env var fallback (`ANTHROPIC_API_KEY`). Singleton via `get_config()`.
- **Data classes**: `DocumentMetrics`, `RepositoryStats`, `ValidationIssue` (with `IssueLevel` enum).
- **Lazy initialization**: Anthropic client created only when AI features are used.
- **Path handling**: Consistent `pathlib.Path` usage throughout.
- **Gap analysis auto-save**: Results saved to `_Gap_Analysis/` with ISO timestamps.

## Code Style

- Line length: 100 characters
- Ruff rules: E, F, I, N, W, UP (pyflakes, isort, pep8-naming, pyupgrade)
- Type hints used throughout (no runtime validation)
- Target Python: 3.10+
