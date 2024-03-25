import os
import re
from importlib.util import find_spec
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


def test_no_inputs(runner: CliRunner):
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert result.output == "No files or modules given. Nothing to do!\n"


def test_module_doesnt_exist(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "foo"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert result.output == (
        "ERROR: No module named 'foo'.\n\n"
        "See slotscheck.rtfd.io/en/latest/discovery.html\n"
        "for help resolving common import problems.\n"
    )


def test_python_file_not_in_sys_path(runner: CliRunner, tmp_path: Path):
    file = tmp_path / "foo.py"
    file.write_text('print("Hello, world!")', encoding="utf-8")
    result = runner.invoke(cli, [str(file)])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert re.fullmatch(
        "ERROR: File '.*/foo.py' is not in PYTHONPATH.\n\n"
        "See slotscheck.rtfd.io/en/latest/discovery.html\n"
        "for help resolving common import problems.\n",
        result.output,
    )


def test_module_is_uninspectable(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "broken.submodule"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: Failed to import 'broken.submodule'.
Oh no, found some problems!
Scanned 0 module(s), 0 class(es).
"""
    )


def test_module_is_uninspectable_no_strict_imports(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "broken.submodule", "--no-strict-imports"]
    )
    assert result.exit_code == 0
    assert (
        result.output
        == """\
NOTE:  Failed to import 'broken.submodule'.
All OK!
Scanned 0 module(s), 0 class(es).
"""
    )


def test_path_doesnt_exist(runner: CliRunner):
    result = runner.invoke(cli, ["doesnt_exist"])
    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
Usage: slotscheck [OPTIONS] [FILES]...
Try 'slotscheck --help' for help.

Error: Invalid value for '[FILES]...': Path 'doesnt_exist' does not exist.
"""
    )


def test_everything_ok(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_ok"])
    assert result.exit_code == 0
    assert result.output == "All OK!\nScanned 6 module(s), 64 class(es).\n"


def test_single_file_module(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "module_singular"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert result.output == "All OK!\nScanned 1 module(s), 5 class(es).\n"


def test_builtins(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "builtins"])
    assert result.exit_code == 0


def test_extension(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "ujson"])
    assert result.exit_code == 0
    assert result.output == ("All OK!\nScanned 1 module(s), 1 class(es).\n")


def test_success_verbose(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "module_ok", "-v"], catch_exceptions=False
    )
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


def test_submodule(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "module_ok.a.b"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert result.output == "All OK!\nScanned 4 module(s), 32 class(es).\n"


def test_namespaced(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "namespaced.module"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert result.output == "All OK!\nScanned 4 module(s), 1 class(es).\n"


def test_implicitly_namespaced(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "implicitly_namespaced"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert result.output == "All OK!\nScanned 8 module(s), 2 class(es).\n"


def test_multiple_modules(runner: CliRunner):
    result = runner.invoke(
        cli,
        ["-m", "module_singular", "-m", "module_ok", "-m", "namespaced"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output == "All OK!\nScanned 11 module(s), 70 class(es).\n"


def test_implicitly_namespaced_path(runner: CliRunner):
    result = runner.invoke(
        cli,
        [str(EXAMPLES_DIR / "implicitly_namespaced")],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output == "All OK!\nScanned 7 module(s), 1 class(es).\n"


def test_multiple_paths(runner: CliRunner):
    result = runner.invoke(
        cli,
        [
            str(EXAMPLES_DIR / "module_singular.py"),
            str(EXAMPLES_DIR / "module_ok/a/b/../b"),
            str(EXAMPLES_DIR / "namespaced/module/foo.py"),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output == "All OK!\nScanned 8 module(s), 38 class(es).\n"


def test_path_is_module_directory(runner: CliRunner):
    # let's define the path indirectly to ensure it works
    path = str(EXAMPLES_DIR / "module_ok/a/../")
    result = runner.invoke(cli, [path], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "All OK!\nScanned 6 module(s), 64 class(es).\n"


def test_cannot_pass_both_path_and_module(runner: CliRunner):
    result = runner.invoke(cli, ["module_ok", "-m", "click"])
    assert result.exit_code == 2
    assert (
        result.output
        == "ERROR: Specify either FILES argument or `-m/--module` "
        "option, not both.\n"
    )


def test_errors_with_default_settings(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_not_ok"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
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
ERROR: 'module_not_ok.foo:Z' has duplicate slots.
ERROR: 'module_not_ok.foo:Za' defines overlapping slots.
ERROR: 'module_not_ok.foo:Zb' has slots but superclass does not.
Oh no, found some problems!
Scanned 4 module(s), 32 class(es).
"""
    )


def test_errors_require_slots_subclass(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_not_ok", "--require-subclass"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:A' has no slots, but it could have.
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:A' has no slots, but it could have.
ERROR: 'module_not_ok.foo:C' has no slots, but it could have.
ERROR: 'module_not_ok.foo:R' has no slots, but it could have.
ERROR: 'module_not_ok.foo:S' has slots but superclass does not.
ERROR: 'module_not_ok.foo:T' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
ERROR: 'module_not_ok.foo:Z' has duplicate slots.
ERROR: 'module_not_ok.foo:Za' defines overlapping slots.
ERROR: 'module_not_ok.foo:Zb' has slots but superclass does not.
Oh no, found some problems!
Scanned 4 module(s), 32 class(es).
"""
    )


def test_errors_disallow_nonslot_inherit(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "module_not_ok", "--require-superclass"]
    )
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
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
ERROR: 'module_not_ok.foo:Z' has duplicate slots.
ERROR: 'module_not_ok.foo:Za' defines overlapping slots.
ERROR: 'module_not_ok.foo:Zb' has slots but superclass does not.
Oh no, found some problems!
Scanned 4 module(s), 32 class(es).
"""
    )


def test_errors_no_require_superclass(runner: CliRunner):
    result = runner.invoke(
        cli, ["-m", "module_not_ok", "--no-require-superclass"]
    )
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
ERROR: 'module_not_ok.foo:Z' has duplicate slots.
ERROR: 'module_not_ok.foo:Za' defines overlapping slots.
Oh no, found some problems!
Scanned 4 module(s), 32 class(es).
"""
    )


def test_errors_with_exclude_classes(runner: CliRunner):
    result = runner.invoke(
        cli,
        ["-m", "module_not_ok", "--exclude-classes", "(foo:U$|:(W|S))"],
    )
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
ERROR: 'module_not_ok.foo:T' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:Z' has duplicate slots.
ERROR: 'module_not_ok.foo:Za' defines overlapping slots.
ERROR: 'module_not_ok.foo:Zb' has slots but superclass does not.
Oh no, found some problems!
Scanned 4 module(s), 32 class(es).
"""
    )


def test_errors_with_include_classes(runner: CliRunner):
    result = runner.invoke(
        cli,
        ["-m", "module_not_ok", "--include-classes", "(foo:.*a|:(W|S))"],
    )
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.foo:S' has slots but superclass does not.
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
ERROR: 'module_not_ok.foo:Za' defines overlapping slots.
Oh no, found some problems!
Scanned 4 module(s), 32 class(es).
"""
    )


def test_errors_with_include_modules(runner: CliRunner):
    result = runner.invoke(
        cli,
        [
            "-m",
            "module_not_ok",
            "--include-modules",
            "(module_not_ok$ | a)",
        ],
    )
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
Oh no, found some problems!
Scanned 3 module(s), 2 class(es).
"""
    )


def test_ignores_given_module_completely(runner: CliRunner):
    result = runner.invoke(
        cli,
        [
            "-m",
            "module_not_ok",
            "--include-modules",
            "nomatch",
        ],
    )
    assert result.exit_code == 0
    assert (
        result.output
        == "Files or modules given, but filtered out by exclude/include. "
        "Nothing to do!\n"
    )


def test_module_not_ok_verbose(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_not_ok", "-v"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.a.b:U' has slots but superclass does not.
       Superclasses without slots:
       - 'module_not_ok.a.b:A'
ERROR: 'module_not_ok.foo:S' has slots but superclass does not.
       Superclasses without slots:
       - 'module_not_ok.foo:R'
ERROR: 'module_not_ok.foo:T' has slots but superclass does not.
       Superclasses without slots:
       - 'module_not_ok.foo:A'
ERROR: 'module_not_ok.foo:U' has slots but superclass does not.
       Superclasses without slots:
       - 'module_not_ok.foo:L'
       - 'module_not_ok.foo:D'
       - 'module_not_ok.foo:C'
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
       Slots already defined in superclass:
       - 'w' (module_not_ok.foo:Q)
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
       Slots already defined in superclass:
       - 'w' (module_not_ok.foo:U.Ua)
       - 'w' (module_not_ok.foo:Q)
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
       Slots already defined in superclass:
       - 'p' (module_not_ok.foo:U)
       - 'v' (module_not_ok.foo:V)
ERROR: 'module_not_ok.foo:Z' has duplicate slots.
       Duplicate slot names:
       - 'b'
       - 'c'
ERROR: 'module_not_ok.foo:Za' defines overlapping slots.
       Slots already defined in superclass:
       - 'b' (module_not_ok.foo:Z)
       - 'c' (module_not_ok.foo:Z)
ERROR: 'module_not_ok.foo:Zb' has slots but superclass does not.
       Superclasses without slots:
       - 'module_not_ok.foo:MyProto'
Oh no, found some problems!
stats:
  modules:     4
    checked:   4
    excluded:  0
    skipped:   0

  classes:     32
    has slots: 23
    no slots:  9
    n/a:       0
"""
    )


def test_module_misc(runner: CliRunner):
    result = runner.invoke(
        cli,
        ["-m", "module_misc", "--no-strict-imports"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (
        result.output
        == """\
NOTE:  Failed to import 'module_misc.a.evil'.
All OK!
Scanned 18 module(s), 8 class(es).
"""
    )


def test_module_exclude(runner: CliRunner):
    result = runner.invoke(
        cli,
        [
            "-m",
            "module_misc",
            "--exclude-modules",
            "evil",
            "--no-strict-imports",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (
        result.output
        == """\
NOTE:  Failed to import 'module_misc.a.b.__main__'.
All OK!
Scanned 16 module(s), 9 class(es).
"""
    )

    from module_misc import a  # type: ignore

    assert not a.evil_was_imported


def test_module_disallow_import_failures(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_misc", "--strict-imports"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: Failed to import 'module_misc.a.evil'.
Oh no, found some problems!
Scanned 18 module(s), 8 class(es).
"""
    )


def test_module_allow_import_failures(runner: CliRunner):
    result = runner.invoke(cli, ["-m", "module_misc", "--no-strict-imports"])
    assert result.exit_code == 0
    assert (
        result.output
        == """\
NOTE:  Failed to import 'module_misc.a.evil'.
All OK!
Scanned 18 module(s), 8 class(es).
"""
    )


def test_finds_config(runner: CliRunner, mocker, tmpdir):
    (tmpdir / "myconf.toml").write_binary(
        b"""
[tool.slotscheck]
require-superclass = false
"""
    )
    mocker.patch(
        "slotscheck.config.find_config_file",
        return_value=Path(tmpdir / "myconf.toml"),
    )
    result = runner.invoke(cli, ["-m", "module_not_ok"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
ERROR: 'module_not_ok.foo:Z' has duplicate slots.
ERROR: 'module_not_ok.foo:Za' defines overlapping slots.
Oh no, found some problems!
Scanned 4 module(s), 32 class(es).
"""
    )


def test_given_config(runner: CliRunner, tmpdir):
    my_config = tmpdir / "myconf.toml"
    my_config.write_binary(
        b"""
[tool.slotscheck]
require-superclass = false
"""
    )
    result = runner.invoke(
        cli,
        ["-m", "module_not_ok", "--settings", str(my_config)],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
ERROR: 'module_not_ok.foo:U.Ua' defines overlapping slots.
ERROR: 'module_not_ok.foo:U.Ub' defines overlapping slots.
ERROR: 'module_not_ok.foo:W' defines overlapping slots.
ERROR: 'module_not_ok.foo:Z' has duplicate slots.
ERROR: 'module_not_ok.foo:Za' defines overlapping slots.
Oh no, found some problems!
Scanned 4 module(s), 32 class(es).
"""
    )


def test_ambiguous_import(runner: CliRunner):
    result = runner.invoke(
        cli,
        [str(EXAMPLES_DIR / "other/module_misc/a/b/c.py")],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        result.output
        == """\
Cannot check due to import ambiguity.
The given files do not correspond with what would be imported:

  'import module_misc.a.b.c' would load from:
  {}
  instead of:
  {}

You may need to define $PYTHONPATH or run as 'python -m slotscheck'
to ensure the correct files can be imported.

See slotscheck.rtfd.io/en/latest/discovery.html
for more information on why this happens and how to resolve it.
""".format(
            find_spec(
                "module_misc.a.b.c"
            ).loader.path,  # type: ignore[union-attr]
            EXAMPLES_DIR / "other/module_misc/a/b/c.py",
        )
    )


def test_ambiguous_import_excluded(runner: CliRunner):
    result = runner.invoke(
        cli,
        ["other/module_misc/a/b/c.py", "--exclude-modules", "module_misc"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (
        result.output
        == """\
Files or modules given, but filtered out by exclude/include. Nothing to do!
"""
    )
