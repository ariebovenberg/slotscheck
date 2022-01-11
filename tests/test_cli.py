import re

import pytest
from click.testing import CliRunner

from slotscheck.cli import DEFAULT_EXCLUDE_RE
from slotscheck.cli import root as cli


@pytest.fixture()
def runner():
    return CliRunner()


def test_no_module(runner: CliRunner):
    result = runner.invoke(cli, [])
    assert result.exit_code == 2
    assert (
        result.output
        == """\
Usage: slotscheck [OPTIONS] MODULENAME
Try 'slotscheck --help' for help.

Error: Missing argument 'MODULENAME'.
"""
    )


def test_module_doesnt_exist(runner: CliRunner):
    result = runner.invoke(cli, ["foo"])
    assert result.exit_code == 2
    assert result.output == "ERROR: Module 'foo' not found.\n"


def test_module_ok(runner: CliRunner):
    result = runner.invoke(cli, ["module_ok"])
    assert result.exit_code == 0
    assert result.output == "All OK!\n"


def test_module_single(runner: CliRunner):
    result = runner.invoke(cli, ["module_singular"])
    assert result.exit_code == 0
    assert result.output == "All OK!\n"


def test_module_builtins(runner: CliRunner):
    result = runner.invoke(cli, ["builtins"])
    assert result.exit_code == 2
    assert result.output == (
        "ERROR: Module 'builtins' cannot be inspected. "
        "Is it an extension module?\n"
    )


def test_module_ok_verbose(runner: CliRunner):
    result = runner.invoke(cli, ["module_ok", "-v"])
    assert result.exit_code == 0
    assert (
        result.output
        == """\
All OK!

stats:
  modules:     7
    checked:   6
    excluded:  1
    skipped:   0

  classes:     64
    has slots: 44
    no slots:  20
    n/a:       0
"""
    )


def test_module_not_ok(runner: CliRunner):
    result = runner.invoke(cli, ["module_not_ok"])
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but inherits from non-slot class.
ERROR: 'module_not_ok.foo:S' has slots but inherits from non-slot class.
ERROR: 'module_not_ok.foo:T' has slots but inherits from non-slot class.
ERROR: 'module_not_ok.foo:U' has slots but inherits from non-slot class.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
Oh no, found some problems!
"""
    )


def test_module_not_ok_excludes_classes(runner: CliRunner):
    result = runner.invoke(
        cli, ["module_not_ok", "--exclude-classes", "(.*?foo:U|.*:(W|S))"]
    )
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but inherits from non-slot class.
ERROR: 'module_not_ok.foo:T' has slots but inherits from non-slot class.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
Oh no, found some problems!
"""
    )


def test_module_not_ok_verbose(runner: CliRunner):
    result = runner.invoke(cli, ["module_not_ok", "-v"])
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but inherits from non-slot class.
       - module_not_ok.a.b:A
ERROR: 'module_not_ok.foo:S' has slots but inherits from non-slot class.
       - module_not_ok.foo:R
ERROR: 'module_not_ok.foo:T' has slots but inherits from non-slot class.
       - module_not_ok.foo:A
ERROR: 'module_not_ok.foo:U' has slots but inherits from non-slot class.
       - module_not_ok.foo:L
       - module_not_ok.foo:D
       - module_not_ok.foo:C
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
       - w
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
       - p
       - v
Oh no, found some problems!

stats:
  modules:     4
    checked:   4
    excluded:  0
    skipped:   0

  classes:     24
    has slots: 18
    no slots:  6
    n/a:       0
"""
    )


def test_module_misc(runner: CliRunner):
    result = runner.invoke(cli, ["module_misc"])
    assert result.exit_code == 0
    assert (
        result.output
        == """\
NOTE:  Failed to import 'module_misc.a.evil'.
All OK!
"""
    )


def test_module_exclude(runner: CliRunner):
    result = runner.invoke(
        cli, ["module_misc", "--exclude-modules", ".* evil .*"]
    )
    assert result.exit_code == 0
    assert (
        result.output
        == """\
NOTE:  Failed to import 'module_misc.a.b.__main__'.
All OK!
"""
    )

    from module_misc import a

    assert not a.evil_was_imported


def test_module_disallow_import_failures(runner: CliRunner):
    result = runner.invoke(cli, ["module_misc", "--strict-imports"])
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: Failed to import 'module_misc.a.evil'.
Oh no, found some problems!
"""
    )


@pytest.mark.parametrize(
    "string, expect",
    [
        ("__main__", True),
        ("__main__.bla.foo", True),
        ("fz.k.__main__.bla.foo", True),
        ("fz.k.__main__", True),
        ("Some__main__", False),
        ("fr.__main__thing", False),
    ],
)
def test_default_exclude(string, expect):
    assert bool(re.fullmatch(DEFAULT_EXCLUDE_RE, string)) is expect
