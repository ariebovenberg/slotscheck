import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from slotscheck.cli import root as cli

from .conftest import EXAMPLES_DIR


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def set_cwd(request):
    os.chdir(EXAMPLES_DIR)
    yield
    os.chdir(request.config.invocation_dir)


def test_no_argument(runner: CliRunner):
    result = runner.invoke(cli, [])
    assert result.exit_code == 2
    assert (
        result.output
        == """\
Usage: slotscheck [OPTIONS]
Try 'slotscheck --help' for help.

Error: Missing option '-m' / '--module'.
"""
    )


def test_module_doesnt_exist(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "foo"])
    assert result.exit_code == 2
    assert result.output == "ERROR: Module 'foo' not found.\n"


def test_everything_ok(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_ok"])
    assert result.exit_code == 0
    assert result.output == "All OK!\n"


def test_single_file_module(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_singular"])
    assert result.exit_code == 0
    assert result.output == "All OK!\n"


def test_builtins(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "builtins"])
    assert result.exit_code == 2
    assert result.output == (
        "ERROR: Module 'builtins' cannot be inspected. "
        "Is it an extension module?\n"
    )


def test_success_verbose(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_ok", "-v"])
    assert result.exit_code == 0
    assert (
        result.output
        == """\
stats:
  modules:     7
    checked:   6
    excluded:  1
    skipped:   0

  classes:     64
    has slots: 44
    no slots:  20
    n/a:       0

All OK!
"""
    )


def test_errors_with_default_settings(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_not_ok"])
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:S' has slots but superclass does not.
ERROR: 'module_not_ok.foo:T' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
Oh no, found some problems!
"""
    )


def test_errors_require_slots_subclass(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_not_ok", "--require-subclass"])
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:A' has no slots but superclass does.
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:A' has no slots but superclass does.
ERROR: 'module_not_ok.foo:C' has no slots but superclass does.
ERROR: 'module_not_ok.foo:R' has no slots but superclass does.
ERROR: 'module_not_ok.foo:S' has slots but superclass does not.
ERROR: 'module_not_ok.foo:T' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
Oh no, found some problems!
"""
    )


def test_errors_disallow_nonslot_inherit(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "module_not_ok", "--require-superclass"]
    )
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:S' has slots but superclass does not.
ERROR: 'module_not_ok.foo:T' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
Oh no, found some problems!
"""
    )


def test_errors_no_require_superclass(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "module_not_ok", "--no-require-superclass"]
    )
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
Oh no, found some problems!
"""
    )


def test_errors_with_exclude_classes(runner: CliRunner):
    result = runner.invoke(
        cli,
        ["-m", "module_not_ok", "--exclude-classes", "(.*?foo:U|.*:(W|S))"],
    )
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:T' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
Oh no, found some problems!
"""
    )


def test_errors_with_include_classes(runner: CliRunner):
    result = runner.invoke(
        cli,
        ["-m", "module_not_ok", "--include-classes", "(.*?foo:.*a|.*:(W|S))"],
    )
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.foo:S' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
Oh no, found some problems!
"""
    )


def test_errors_with_include_modules(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "module_not_ok", "--include-modules", ".*a.*"]
    )
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
Oh no, found some problems!
"""
    )


def test_module_not_ok_verbose(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_not_ok", "-v"])
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
       - module_not_ok.a.b:A
ERROR: 'module_not_ok.foo:S' has slots but superclass does not.
       - module_not_ok.foo:R
ERROR: 'module_not_ok.foo:T' has slots but superclass does not.
       - module_not_ok.foo:A
ERROR: 'module_not_ok.foo:U' has slots but superclass does not.
       - module_not_ok.foo:L
       - module_not_ok.foo:D
       - module_not_ok.foo:C
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
       - w (module_not_ok.foo:Q)
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
       - w (module_not_ok.foo:U.Ua)
       - w (module_not_ok.foo:Q)
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
       - p (module_not_ok.foo:U)
       - v (module_not_ok.foo:V)
stats:
  modules:     4
    checked:   4
    excluded:  0
    skipped:   0

  classes:     26
    has slots: 19
    no slots:  7
    n/a:       0

Oh no, found some problems!
"""
    )


def test_module_misc(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_misc"])
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
        cli, ["-m", "module_misc", "--exclude-modules", ".* evil .*"]
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
    result = runner.invoke(cli, ["-m", "module_misc", "--strict-imports"])
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: Failed to import 'module_misc.a.evil'.
Oh no, found some problems!
"""
    )


def test_errors_use_toml(runner: CliRunner, mocker, tmpdir):
    (tmpdir / "myconf.toml").write_binary(
        b"""
[tool.slotscheck]
require-superclass = false
"""
    )
    mocker.patch(
        "slotscheck.config.find_pyproject_toml",
        return_value=Path(tmpdir / "myconf.toml"),
    )
    result = runner.invoke(cli, ["-m", "module_not_ok"])
    assert result.exit_code == 1
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
Oh no, found some problems!
"""
    )
