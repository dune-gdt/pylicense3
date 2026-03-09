# pylicense3

[![PyPI version](https://img.shields.io/pypi/v/pylicense3.svg)](https://pypi.org/project/pylicense3)
[![CI](https://github.com/dune-gdt/pylicense3/actions/workflows/ci.yml/badge.svg)](https://github.com/dune-gdt/pylicense3/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/pylicense3/badge/?version=latest)](https://pylicense3.readthedocs.io/en/latest/)

Apply license information to a git project.

## Requirements

- Python `3.10+`
- [uv](https://docs.astral.sh/uv/)

## Quick Start

```bash
uv sync
uv run pylicense3 --help
```

## Development

```bash
uv run --group lint ruff check .
uv run --group lint ruff format .
uv run --group test pytest
uv run --group docs sphinx-build -W -b html docs docs/_build/html
```

Or use `make` wrappers:

```bash
make lint format test docs
```

## Release

Tags matching `v*` trigger `.github/workflows/release.yml`, which builds with `uv build` and publishes to PyPI via `PYPI_TOKEN`.

## License

BSD-2-Clause
