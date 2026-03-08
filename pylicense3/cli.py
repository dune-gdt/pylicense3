#!/usr/bin/env python3

"""Add header to a given file.

Usage:
    pylicense [-hv] [--help] [--verbose] --cfg=CONFIG_FILE PATH

Arguments:
    PATH                   Directory or file to process.

Options:
    --cfg=CONFIG_FILE      Python config file describing header generation.
    -h, --help             Show this message.
    -v, --verbose          Be verbose.
"""

from __future__ import annotations

import fnmatch
import importlib.util
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from docopt import docopt


class GitError(Exception):
    """Raised when git metadata required for header generation cannot be computed."""


def _compile_patterns(patterns: list[str]) -> re.Pattern[str]:
    if not patterns:
        patterns = ['*']
    return re.compile('|'.join(fnmatch.translate(pattern) for pattern in patterns))


def _format_year_range(year_range: int | tuple[int, int]) -> str:
    if isinstance(year_range, tuple):
        start, end = year_range
        return f'{start} - {end}'
    return f'{year_range}'


def process_dir(dirname: str, config):
    candidate = Path(dirname)
    if candidate.is_file():
        yield str(candidate), ''
        return

    if not candidate.is_dir():
        raise FileNotFoundError(dirname)

    include = _compile_patterns(getattr(config, 'include_patterns', ['*']))
    exclude_patterns = getattr(config, 'exclude_patterns', [])
    exclude = _compile_patterns(exclude_patterns) if exclude_patterns else None

    root = candidate.resolve()
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue

        relative_path = path.relative_to(root).as_posix()
        if include.match(relative_path) and (exclude is None or not exclude.match(relative_path)):
            yield str(path), str(root)


def get_git_authors(filename: str, root: str) -> dict[str, str]:
    years_per_author: dict[str, set[int]] = defaultdict(set)
    filename_path = Path(filename)
    root_path = Path(root)

    try:
        relative_path = filename_path.resolve().relative_to(root_path.resolve())
    except ValueError:
        relative_path = filename_path

    command = [
        'git',
        'log',
        '--use-mailmap',
        '--follow',
        '--pretty=format:%aN %ad',
        '--date=format:%Y',
        str(relative_path),
    ]

    try:
        output = subprocess.check_output(command, text=True, cwd=root)
    except subprocess.CalledProcessError as error:
        raise GitError('failed to extract authors from git history!') from error

    for line in sorted(set(output.splitlines())):
        author_and_year = line.strip().rsplit(' ', 1)
        if len(author_and_year) != 2:
            continue

        author, year_text = author_and_year
        try:
            year = int(year_text)
        except ValueError:
            continue
        years_per_author[author].add(year)

    authors: dict[str, str] = {}
    for author, years in years_per_author.items():
        if not years:
            continue

        sorted_years = sorted(years)
        year_ranges: list[int | tuple[int, int]] = []
        start_year = sorted_years[0]
        end_year = start_year

        for year in sorted_years[1:]:
            if year == end_year + 1:
                end_year = year
                continue
            year_ranges.append((start_year, end_year) if end_year > start_year else start_year)
            start_year = year
            end_year = year

        year_ranges.append((start_year, end_year) if end_year > start_year else start_year)
        authors[author] = ', '.join(_format_year_range(year_range) for year_range in year_ranges)

    return authors


def read_current_header(source_iter, prefix, project_name, copyright_statement, license_str, url, lead_in, lead_out):
    header = {'shebang': None, 'encoding': None, 'comments': []}
    warning = ''
    could_be_an_author = False
    while True:
        line = next(source_iter)
        if line is None:
            break

        dirt_to_remove = ['\xef', '\xbb', '\xbf']
        while len(line) > 0 and line[0] in dirt_to_remove:
            for dirt in dirt_to_remove:
                line = line.lstrip(dirt)

        if len(line) == 0:
            break
        if line.startswith('#!') and len(line.strip()) > 2:
            header['shebang'] = line.strip()
            continue
        if (lead_in and lead_in in line) or (lead_out and lead_out in line):
            continue
        if not line.startswith(prefix):
            break

        can_be_discarded = ['Copyright', 'copyright', 'License']
        for entry in (project_name, copyright_statement, license_str):
            for raw_line in entry.split('\n'):
                can_be_discarded.append(raw_line.strip().lstrip(prefix).strip())

        line_without_prefix = line[len(prefix) :].strip()
        if re.match(r'.*coding[:=]\s*', line):
            header['encoding'] = line[len(prefix) :]
        elif any(line_without_prefix.startswith(discard) for discard in can_be_discarded) or (
            url and line_without_prefix.startswith(url)
        ):
            continue
        elif any(line_without_prefix.startswith(some_url) for some_url in ('http://', 'https://')):
            warning = f"dropping url '{line_without_prefix}'!"
        elif line_without_prefix.startswith('Authors:'):
            could_be_an_author = True
            continue
        elif could_be_an_author:
            if line[len(prefix) :].startswith('  ') and line.strip()[-1:] == ')':
                continue
            could_be_an_author = False
            header['comments'].append(line)
        else:
            header['comments'].append(line)

    return header, warning, line


def write_header(
    target,
    header,
    authors,
    license_str,
    prefix,
    project_name,
    url,
    max_width,
    copyright_statement,
    lead_in,
    lead_out,
):
    shebang, encoding = header['shebang'], header['encoding']
    if shebang:
        target.write(f'{shebang}\n')
    if encoding:
        target.write(f'{prefix} {encoding}\n')
    if shebang or encoding:
        target.write(f'{prefix}\n')
    if lead_in:
        target.write(f'{lead_in}\n')

    line = f'{prefix} {project_name}'
    if url is not None:
        if len(line) + len(url) + len('().') <= max_width:
            target.write(f'{line} ({url}).\n')
        else:
            target.write(f'{line}\n')
            if max_width - len(prefix) - 1 - len(url):
                target.write(f'{prefix}   {url}\n')
            else:
                target.write(f'{prefix} {url}\n')

    target.write(f'{prefix} {copyright_statement}\n')

    l_str = f'\n{prefix}'.join(license_str.split('\n'))
    target.write(f'{prefix} License: {l_str}\n')

    if isinstance(authors, str):
        target.write(f'{prefix} {authors}\n')
    else:
        target.write(f'{prefix} Authors:\n')
        max_author_length = max((len(author) for author in authors), default=0)
        for author in sorted(authors.keys()):
            year = f'({authors[author]})'
            padded_author = author
            if len(prefix) + 4 + max_author_length + len(year) <= max_width:
                padded_author = author.ljust(max_author_length)
            target.write(f'{prefix}   {padded_author} {year}\n')

    def prune_first_empty_comments(lines):
        first_real_comment_line = False
        result = []
        for raw_line in lines:
            raw_line = raw_line.strip()
            if first_real_comment_line:
                result.append(raw_line)
            elif len(raw_line[len(prefix) :].strip()) > 0:
                first_real_comment_line = True
                result.append(raw_line)
        return result

    comments = header['comments']
    if comments:
        comments.reverse()
        comments = prune_first_empty_comments(comments)
        comments.reverse()
        comments = prune_first_empty_comments(comments)
        if comments:
            target.write(f'{prefix}\n')
        for comment in comments:
            target.write(f'{comment}\n')
    if lead_out:
        target.write(f'{lead_out}\n')


def process_file(filename, config, root):
    project_name = config.name.strip()
    license_str = config.license
    url = getattr(config, 'url', None)
    copyright_statement = getattr(
        config,
        'copyright_statement',
        'The copyright lies with the authors of this file (see below).',
    )
    max_width = getattr(config, 'max_width', 78)
    prefix = getattr(config, 'prefix', '#')
    lead_out = getattr(config, 'lead_out', None)
    lead_in = getattr(config, 'lead_in', None)
    authors = getattr(config, 'contributors_team', get_git_authors(filename, root))

    with open(filename, encoding='utf-8', errors='surrogateescape') as source_file:
        source = source_file.readlines()

    source.append(None)
    source_iter = iter(source)

    print('*' * 88)
    print(license_str)
    print('*' * 88)
    header, warning, last_header_line = read_current_header(
        source_iter,
        prefix,
        project_name,
        copyright_statement,
        license_str,
        url,
        lead_in,
        lead_out,
    )

    line = last_header_line
    with open(filename, 'w', encoding='utf-8', errors='surrogateescape') as target:
        while line is not None and line.isspace():
            line = next(source_iter)

        write_header(
            target,
            header,
            authors,
            license_str,
            prefix,
            project_name,
            url,
            max_width,
            copyright_statement,
            lead_in,
            lead_out,
        )
        target.write('\n')

        while line is not None:
            target.write(line)
            line = next(source_iter)

    return warning


def main():
    args = docopt(__doc__)
    cfg = args['--cfg']

    spec = importlib.util.spec_from_file_location('config', cfg)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'failed to load config from {cfg!r}')

    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)

    for filename, dirname in process_dir(args['PATH'], config):
        display_name = filename[len(dirname) :] if dirname and filename.startswith(dirname) else filename
        print(f'{display_name}: ', end='')
        try:
            result = process_file(filename, config, dirname if dirname else '.')
            print(result if result else 'success')
        except GitError as error:
            print(error)


if __name__ == '__main__':
    main()
