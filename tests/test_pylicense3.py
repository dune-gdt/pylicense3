#!/usr/bin/env python

"""Tests for `pylicense3` package."""

from io import StringIO
from pathlib import Path

from pylicense3.cli import (
    _compile_patterns,
    _format_year_range,
    get_git_authors,
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
    header, warning, last_line = read_current_header(
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
    assert warning == ''
    assert last_line == '\n'


def test_read_current_header_warns_about_stray_url():
    source = ['# https://stray.example/link\n', '\n', None]
    _header, warning, _last_line = read_current_header(
        iter(source),
        prefix='#',
        project_name='Example Project',
        copyright_statement='Copyright statement here',
        license_str='BSD-2-Clause',
        url=None,
        lead_in=None,
        lead_out=None,
    )

    assert 'stray.example' in warning


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


def test_process_file_rewrites_header_and_preserves_body(git_repo, make_config):
    # Ensure HEAD exists so the eager git-author lookup returns cleanly.
    git_repo.commit('seed.txt', 'seed\n', 'Seed', 'seed@example.com', 2019)
    source = git_repo.path / 'mod.py'
    source.write_text('print("hello")\n')
    config = make_config(url='https://example.org', contributors_team='Alice (2020)')

    warning = process_file(str(source), config, str(git_repo.path))

    result = source.read_text()
    assert '# Example Project (https://example.org).' in result
    assert '# Alice (2020)' in result
    assert 'print("hello")' in result
    assert warning == ''


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
