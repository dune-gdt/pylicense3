.PHONY: sync lint format test docs build publish precommit

sync:
	uv sync

lint:
	uv run --group lint ruff check .

format:
	uv run --group lint ruff format .

test:
	uv run --group test pytest

docs:
	uv run --group docs sphinx-build -W -b html docs docs/_build/html

build:
	uv build

publish:
	uv run --group release twine upload dist/*

precommit:
	uv run --group lint pre-commit run --all-files
