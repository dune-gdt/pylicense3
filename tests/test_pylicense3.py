#!/usr/bin/env python

"""Tests for `pylicense3` package."""

from io import StringIO
from pathlib import Path

import pytest

from pylicense3.cli import (
    GitError,
    _compile_patterns,
    _format_year_range,
    get_git_authors,
    main,
    process_dir,
    process_file,
    read_current_header,
    write_header,
)


def test_version():
    import pylicense3

    assert pylicense3.__version__


def test_import():
    import pylicense3

    assert pylicense3 is not None


def test_compile_patterns_defaults_to_match_all():
    pattern = _compile_patterns([])
    assert pattern.match('anything/at/all.py')


def test_compile_patterns_matches_globs():
    pattern = _compile_patterns(['*.py'])
    assert pattern.match('module.py')
    assert not pattern.match('module.txt')


def test_format_year_range_single_year():
    assert _format_year_range(2020) == '2020'


def test_format_year_range_span():
    assert _format_year_range((2020, 2023)) == '2020 - 2023'


def test_get_git_authors_collapses_consecutive_years(git_repo):
    git_repo.commit('file.py', 'v1\n', 'Alice', 'alice@example.com', 2020)
    git_repo.commit('file.py', 'v2\n', 'Alice', 'alice@example.com', 2021)
    git_repo.commit('file.py', 'v3\n', 'Bob', 'bob@example.com', 2022)
    git_repo.commit('file.py', 'v4\n', 'Alice', 'alice@example.com', 2024)

    authors = get_git_authors(str(git_repo.path / 'file.py'), str(git_repo.path))

    assert authors['Alice'] == '2020 - 2021, 2024'
    assert authors['Bob'] == '2022'


def test_read_current_header_parses_and_discards_boilerplate():
    source = [
        '#!/usr/bin/env python\n',
        '# -*- coding: utf-8 -*-\n',
        '# Example Project (https://example.org).\n',
        '# The copyright lies with the authors of this file (see below).\n',
        '# License: BSD-2-Clause\n',
        '# Authors:\n',
        '#   Alice (2020)\n',
        '# keep this comment\n',
        '\n',
        None,
    ]
    header, warnings, last_line = read_current_header(
        iter(source),
        prefix='#',
        project_name='Example Project',
        copyright_statement='The copyright lies with the authors of this file (see below).',
        license_str='BSD-2-Clause',
        url='https://example.org',
        lead_in=None,
        lead_out=None,
    )

    assert header['shebang'] == '#!/usr/bin/env python'
    assert 'coding' in (header['encoding'] or '')
    assert any('keep this comment' in comment for comment in header['comments'])
    # Regenerated boilerplate must not survive into the preserved comments.
    assert not any('Example Project' in comment for comment in header['comments'])
    assert not any('Authors' in comment for comment in header['comments'])
    assert warnings == []
    assert last_line == '\n'


def test_read_current_header_warns_about_stray_url():
    source = ['# https://stray.example/link\n', '\n', None]
    _header, warnings, _last_line = read_current_header(
        iter(source),
        prefix='#',
        project_name='Example Project',
        copyright_statement='Copyright statement here',
        license_str='BSD-2-Clause',
        url=None,
        lead_in=None,
        lead_out=None,
    )

    assert len(warnings) == 1
    assert 'stray.example' in warnings[0]


def test_read_current_header_collects_every_stray_url():
    source = ['# https://first.example/link\n', '# http://second.example/link\n', '\n', None]
    _header, warnings, _last_line = read_current_header(
        iter(source),
        prefix='#',
        project_name='Example Project',
        copyright_statement='Copyright statement here',
        license_str='BSD-2-Clause',
        url=None,
        lead_in=None,
        lead_out=None,
    )

    # A second stray url must not overwrite the first one.
    assert len(warnings) == 2
    assert 'first.example' in warnings[0]
    assert 'second.example' in warnings[1]


def test_write_header_renders_full_block():
    header = {'shebang': '#!/usr/bin/env python', 'encoding': None, 'comments': ['# keep me\n']}
    target = StringIO()

    write_header(
        target,
        header,
        {'Alice': '2020'},
        license_str='BSD-2-Clause',
        prefix='#',
        project_name='Example Project',
        url='https://example.org',
        max_width=78,
        copyright_statement='Copyright statement here',
        lead_in=None,
        lead_out=None,
    )

    text = target.getvalue()
    assert '#!/usr/bin/env python' in text
    assert '# Example Project (https://example.org).' in text
    assert '# Copyright statement here' in text
    assert '# License: BSD-2-Clause' in text
    assert '# Authors:' in text
    assert 'Alice (2020)' in text
    assert '# keep me' in text


def _write_header_url_lines(url: str, max_width: int) -> list[str]:
    """Render a header for ``url`` and return the project name/url lines."""
    target = StringIO()
    write_header(
        target,
        {'shebang': None, 'encoding': None, 'comments': []},
        'Alice (2020)',
        license_str='BSD-2-Clause',
        prefix='#',
        project_name='Example Project',
        url=url,
        max_width=max_width,
        copyright_statement='Copyright statement here',
        lead_in=None,
        lead_out=None,
    )

    return target.getvalue().splitlines()[:2]


def test_write_header_indents_wrapped_url_when_it_fits():
    url = 'https://example.org/some/long/path'
    # 17 (project line) + 34 (url) + 3 does not fit into 40, so the url wraps;
    # the indented url line is 38 characters and still fits.
    lines = _write_header_url_lines(url, max_width=40)

    assert lines == ['# Example Project', f'#   {url}']
    assert len(lines[1]) <= 40


def test_write_header_falls_back_to_single_space_when_indent_does_not_fit():
    url = 'https://example.org/some/long/path'
    # The indented url would need 38 characters, so only a single space fits.
    lines = _write_header_url_lines(url, max_width=36)

    assert lines == ['# Example Project', f'# {url}']
    assert len(lines[1]) <= 36


def test_process_file_rewrites_header_and_preserves_body(git_repo, make_config):
    # Ensure HEAD exists so the eager git-author lookup returns cleanly.
    git_repo.commit('seed.txt', 'seed\n', 'Seed', 'seed@example.com', 2019)
    source = git_repo.path / 'mod.py'
    source.write_text('print("hello")\n')
    config = make_config(url='https://example.org', contributors_team='Alice (2020)')

    result = process_file(str(source), config, str(git_repo.path))

    rewritten = source.read_text()
    assert '# Example Project (https://example.org).' in rewritten
    assert '# Alice (2020)' in rewritten
    assert 'print("hello")' in rewritten
    assert result.changed
    assert result.warnings == []


def test_process_file_reports_unchanged_on_second_run(git_repo, make_config):
    git_repo.commit('mod.py', 'print("hello")\n', 'Alice', 'alice@example.com', 2020)
    source = git_repo.path / 'mod.py'
    config = make_config(url='https://example.org')

    assert process_file(str(source), config, str(git_repo.path)).changed
    already_applied = source.read_text()
    mtime = source.stat().st_mtime_ns

    result = process_file(str(source), config, str(git_repo.path))

    assert not result.changed
    assert source.read_text() == already_applied
    # A file whose header is already up to date must not be touched at all.
    assert source.stat().st_mtime_ns == mtime


def test_process_file_reports_warnings_alongside_changed(git_repo, make_config):
    git_repo.commit('seed.txt', 'seed\n', 'Seed', 'seed@example.com', 2019)
    source = git_repo.path / 'mod.py'
    source.write_text('# https://stray.example/link\n\nprint("hello")\n')
    config = make_config(url='https://example.org', contributors_team='Alice (2020)')

    result = process_file(str(source), config, str(git_repo.path))

    assert result.changed
    assert len(result.warnings) == 1
    assert 'stray.example' in result.warnings[0]


def test_process_dir_applies_include_and_exclude(tmp_path, make_config):
    (tmp_path / 'a.py').write_text('x\n')
    (tmp_path / 'b.txt').write_text('x\n')
    sub = tmp_path / 'sub'
    sub.mkdir()
    (sub / 'c.py').write_text('x\n')

    config = make_config(include_patterns=['*.py'], exclude_patterns=['sub/*'])
    results = list(process_dir(str(tmp_path), config))

    names = sorted(Path(filename).name for filename, _root in results)
    assert names == ['a.py']


def test_process_dir_yields_single_file(tmp_path, make_config):
    single = tmp_path / 'only.py'
    single.write_text('x\n')

    results = list(process_dir(str(single), make_config()))

    assert results == [(str(single), '')]


def _write_config(tmp_path):
    """Write a minimal config module for the CLI and return its path."""
    config = tmp_path / 'license_config.py'
    config.write_text("name = 'Example Project'\nlicense = 'BSD-2-Clause'\n")
    return config


def test_main_reports_updated_then_unchanged(git_repo, tmp_path, monkeypatch, capsys):
    git_repo.commit('mod.py', 'print("hello")\n', 'Alice', 'alice@example.com', 2020)
    source = git_repo.path / 'mod.py'
    config = _write_config(tmp_path)
    # A single-file PATH makes the CLI resolve git history against the cwd.
    monkeypatch.chdir(git_repo.path)
    monkeypatch.setattr('sys.argv', ['pylicense3', '--cfg', str(config), str(source)])

    main()
    assert capsys.readouterr().out.strip().endswith(': updated')

    main()
    captured = capsys.readouterr()
    assert captured.out.strip().endswith(': unchanged')
    assert captured.err == ''


def test_main_separates_warnings_from_success(git_repo, tmp_path, monkeypatch, capsys):
    git_repo.commit('mod.py', '# https://stray.example/link\n\nprint("hello")\n', 'Alice', 'alice@example.com', 2020)
    source = git_repo.path / 'mod.py'
    config = _write_config(tmp_path)
    # A single-file PATH makes the CLI resolve git history against the cwd.
    monkeypatch.chdir(git_repo.path)
    monkeypatch.setattr('sys.argv', ['pylicense3', '--cfg', str(config), str(source)])

    main()

    captured = capsys.readouterr()
    # The success signal stays on stdout, the caveat goes to stderr.
    assert captured.out.strip().endswith(': updated')
    assert 'warning: ' in captured.err
    assert 'stray.example' in captured.err


def test_main_reports_failures_on_stderr_and_exits_non_zero(tmp_path, monkeypatch, capsys):
    source = tmp_path / 'mod.py'
    source.write_text('print("hello")\n')
    config = _write_config(tmp_path)
    monkeypatch.setattr('sys.argv', ['pylicense3', '--cfg', str(config), str(source)])

    def fail(*_args, **_kwargs):
        raise GitError('failed to extract authors from git history!')

    monkeypatch.setattr('pylicense3.cli.process_file', fail)

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ''
    assert 'error: failed to extract authors' in captured.err
