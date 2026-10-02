from __future__ import annotations

from click.testing import CliRunner

from cm2 import cli


def test_help_lists_every_command(isolated_home):
    result = CliRunner().invoke(cli.main, ["help"])
    assert result.exit_code == 0
    for name in cli.main.commands:
        assert f"cm2 {name}" in result.output


def test_help_for_one_command(isolated_home):
    result = CliRunner().invoke(cli.main, ["help", "stop"], prog_name="cm2")
    assert result.exit_code == 0
    assert "Usage: cm2 stop [OPTIONS] [STREAM_ID]" in result.output


def test_help_unknown_command_fails(isolated_home):
    result = CliRunner().invoke(cli.main, ["help", "nope"])
    assert result.exit_code == 2
    assert "no command 'nope'" in result.output


def test_short_help_flag(isolated_home):
    result = CliRunner().invoke(cli.main, ["-h"])
    assert result.exit_code == 0
    assert "Commands:" in result.output
