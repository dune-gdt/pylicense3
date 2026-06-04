"""Shared pytest fixtures for the pylicense3 test-suite."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def make_config():
    """Return a factory building a minimal config object understood by the CLI.

    ``cli.process_file`` reads ``config.name`` / ``config.license`` directly and
    looks the rest up via ``getattr``; a ``SimpleNamespace`` mirrors that contract
    without needing an importable module on disk.
    """

    def _make(**overrides: object) -> SimpleNamespace:
        attributes: dict[str, object] = {'name': 'Example Project', 'license': 'BSD-2-Clause'}
        attributes.update(overrides)
        return SimpleNamespace(**attributes)

    return _make


@pytest.fixture
def git_repo(tmp_path: Path):
    """Create an isolated throwaway git repository under ``tmp_path``.

    Returns a namespace exposing the repo ``path`` and a ``commit`` helper that
    records a file with a specific author and calendar year, so author/year
    extraction can be exercised deterministically.
    """
    if shutil.which('git') is None:
        pytest.skip('git is not available')

    repo = tmp_path / 'repo'
    repo.mkdir()

    # Pin config to the repo so the host machine's global identity cannot interfere.
    base_env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_SYSTEM': os.devnull}

    def run(*args: str, env_extra: dict[str, str] | None = None) -> None:
        env = dict(base_env)
        if env_extra:
            env.update(env_extra)
        subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True, text=True, env=env)

    run('init')
    run('config', 'user.name', 'Default User')
    run('config', 'user.email', 'default@example.com')

    def commit(path: str, content: str, author_name: str, author_email: str, year: int) -> None:
        file_path = repo / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        run('add', path)
        date = f'{year}-01-01T00:00:00'
        run(
            'commit',
            '-m',
            f'update {path}',
            env_extra={
                'GIT_AUTHOR_NAME': author_name,
                'GIT_AUTHOR_EMAIL': author_email,
                'GIT_AUTHOR_DATE': date,
                'GIT_COMMITTER_NAME': author_name,
                'GIT_COMMITTER_EMAIL': author_email,
                'GIT_COMMITTER_DATE': date,
            },
        )

    return SimpleNamespace(path=repo, run=run, commit=commit)
