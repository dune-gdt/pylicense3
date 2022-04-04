#!/usr/bin/env python

"""Tests for `pylicense3` package."""
from click.testing import CliRunner


def test_version():
    assert pylicense3.__version__


def test_import():
    import pylicense3


def test_command_line_interface():
    """Test the CLI."""
    from pylicense3 import cli

    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert 'pylicense3.cli.main' in result.output
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    assert '--help  Show this message and exit.' in help_result.output
