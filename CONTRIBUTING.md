# Contributing

## Development Setup

```bash
git clone https://github.com/dune-gdt/pylicense3
cd pylicense3
uv sync
```

The project targets Python `3.10+`.

## Common Commands

```bash
uv run --group lint ruff check .
uv run --group lint ruff format .
uv run --group test pytest
uv run --group docs sphinx-build -W -b html docs docs/_build/html
uv run --group lint pre-commit run --all-files
```

## Pull Requests

1. Create a branch from `main`.
2. Keep changes focused and include tests for behavior changes.
3. Run lint + tests before opening the PR.
4. Update docs when behavior or public usage changes.
