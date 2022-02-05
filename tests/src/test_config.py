import dataclasses
import re
from pathlib import Path

import pytest
import tomli

from slotscheck.config import (
    DEFAULT_MODULE_EXCLUDE_RE,
    Config,
    InvalidKeys,
    InvalidValueType,
    PartialConfig,
    collect,
    find_ini_file,
    find_pyproject_toml,
)

EXAMPLE_TOML = b"""
[tool.foo]
bla = 5

[tool.slotscheck]
require-subclass = true
exclude-modules = '''
(
  .*\\.test\\..*
  |__main__
  |some\\.specific\\.module
)
'''
require-superclass = false
"""

EXAMPLE_INI = """
[foo]
bla = 5

[slotscheck]
require-subclass = false
exclude-modules = (
    .*\\.test\\..*
    |__main__
    |some\\.specific\\.module
    )
require-superclass = false
"""


def test_find_pyproject_toml(tmpdir):
    (tmpdir.ensure_dir("foo", "bar") / "pyproject.toml").write_binary(b"5")
    (tmpdir.ensure_dir("foo") / "pyproject.toml").write_binary(b"3")
    (tmpdir.ensure_dir("foo", "baz") / "pyproject.toml").write_binary(b"1")
    tmpdir.ensure_dir("foo", "qux")
    assert (
        find_pyproject_toml(
            Path(tmpdir / "foo/qux")
        ).read_text()  # type: ignore
        == "3"
    )
    assert (
        find_pyproject_toml(Path(tmpdir / "foo")).read_text()  # type: ignore
        == "3"
    )
    assert (
        find_pyproject_toml(
            Path(tmpdir / "foo/bar")
        ).read_text()  # type: ignore
        == "5"
    )
    assert (
        find_pyproject_toml(
            Path(tmpdir / "foo/baz")
        ).read_text()  # type: ignore
        == "1"
    )
    assert find_pyproject_toml(Path(tmpdir)) is None


def test_find_setup_cfg(tmpdir):
    (tmpdir.ensure_dir("foo", "bar") / "setup.cfg").write_text(
        "5", encoding="utf-8"
    )
    (tmpdir.ensure_dir("foo") / "setup.cfg").write_text("3", encoding="utf-8")
    (tmpdir.ensure_dir("foo", "baz") / "setup.cfg").write_text(
        "1", encoding="utf-8"
    )
    tmpdir.ensure_dir("foo", "qux")
    assert (
        find_ini_file(Path(tmpdir / "foo/qux")).read_text()  # type: ignore
        == "3"
    )
    assert (
        find_ini_file(Path(tmpdir / "foo")).read_text() == "3"  # type: ignore
    )
    assert (
        find_ini_file(Path(tmpdir / "foo/bar")).read_text()  # type: ignore
        == "5"
    )
    assert (
        find_ini_file(Path(tmpdir / "foo/baz")).read_text()  # type: ignore
        == "1"
    )
    assert find_ini_file(Path(tmpdir)) is None


def test_collect(tmpdir):
    (tmpdir / "setup.cfg").write_text(EXAMPLE_INI, encoding="utf-8")
    (tmpdir / "pyproject.toml").write_binary(EXAMPLE_TOML)
    assert collect(
        dataclasses.asdict(Config.EMPTY), Path(tmpdir), None
    ).require_subclass


class TestOptionsApply:
    def test_empty(self):
        assert Config(True, False, True, None, "", "hello", None).apply(
            PartialConfig(None, None, None, None, None, None, None)
        ) == Config(True, False, True, None, "", "hello", None)

    def test_different(self):
        assert Config(True, False, True, None, "", "hello", None).apply(
            PartialConfig(False, None, None, "hi", "", None, None)
        ) == Config(False, False, True, "hi", "", "hello", None)


class TestPartialOptionsFromToml:
    def test_options_from_toml(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(EXAMPLE_TOML)
        Config = PartialConfig.from_toml(Path(tmpdir / "myconf.toml"))
        assert Config == PartialConfig(
            strict_imports=None,
            require_subclass=True,
            require_superclass=False,
            include_modules=None,
            include_classes=None,
            exclude_classes=None,
            exclude_modules="""\
(
  .*\\.test\\..*
  |__main__
  |some\\.specific\\.module
)
""",
        )

    def test_invalid_toml(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(b"[foo inv]alid")
        with pytest.raises(tomli.TOMLDecodeError):
            PartialConfig.from_toml(Path(tmpdir / "myconf.toml"))

    def test_no_slotscheck_section(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(
            b"""
[tool.bla]
k = 5
"""
        )
        assert PartialConfig.from_toml(
            Path(tmpdir / "myconf.toml")
        ) == PartialConfig(None, None, None, None, None, None, None)

    def test_empty_slotscheck_section(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(
            b"""
[tool.slotscheck]
"""
        )
        assert PartialConfig.from_toml(
            Path(tmpdir / "myconf.toml")
        ) == PartialConfig(None, None, None, None, None, None, None)

    def test_empty(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(b"")
        assert PartialConfig.from_toml(
            Path(tmpdir / "myconf.toml")
        ) == PartialConfig(None, None, None, None, None, None, None)

    def test_invalid_keys(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(
            b"""
[tool.slotscheck]
k = 9
strict-imports = true
foo = 4
"""
        )
        with pytest.raises(
            InvalidKeys,
            match=re.escape("Invalid configuration key(s): 'foo', 'k'."),
        ):
            PartialConfig.from_toml(Path(tmpdir / "myconf.toml"))

    def test_invalid_types(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(
            b"""
[tool.slotscheck]
strict-imports = true
include-modules = false
"""
        )
        with pytest.raises(
            InvalidValueType,
            match=re.escape("Invalid value type for 'include-modules'."),
        ):
            PartialConfig.from_toml(Path(tmpdir / "myconf.toml"))


class TestPartialOptionsFromIni:
    def test_options_from_ini(self, tmpdir):
        (tmpdir / "setup.cfg").write_text(EXAMPLE_INI, encoding="utf-8")
        Config = PartialConfig.from_ini(Path(tmpdir / "setup.cfg"))
        assert Config == PartialConfig(
            strict_imports=None,
            require_subclass=False,
            require_superclass=False,
            include_modules=None,
            include_classes=None,
            exclude_classes=None,
            exclude_modules="""\
(
.*\\.test\\..*
|__main__
|some\\.specific\\.module
)""",
        )

    def test_no_slotscheck_section(self, tmpdir):
        (tmpdir / "setup.cfg").write_text(
            """
[tool.bla]
k = 5
""",
            encoding="utf-8",
        )
        assert PartialConfig.from_ini(
            Path(tmpdir / "setup.cfg")
        ) == PartialConfig(None, None, None, None, None, None, None)

    def test_empty_slotscheck_section(self, tmpdir):
        (tmpdir / "myconf.toml").write_text(
            """
[slotscheck]
""",
            encoding="utf-8",
        )
        assert PartialConfig.from_ini(
            Path(tmpdir / "setup.cfg")
        ) == PartialConfig(None, None, None, None, None, None, None)

    def test_empty(self, tmpdir):
        (tmpdir / "setup.cfg").write_text("", encoding="utf-8")
        assert PartialConfig.from_ini(
            Path(tmpdir / "setup.cfg")
        ) == PartialConfig(None, None, None, None, None, None, None)

    def test_invalid_keys(self, tmpdir):
        (tmpdir / "setup.cfg").write_text(
            """
[slotscheck]
k = 9
strict-imports = true
foo = 4
""",
            encoding="utf-8",
        )
        with pytest.raises(
            InvalidKeys,
            match=re.escape("Invalid configuration key(s): 'foo', 'k'."),
        ):
            PartialConfig.from_ini(Path(tmpdir / "setup.cfg"))

    def test_invalid_types(self, tmpdir):
        (tmpdir / "setup.cfg").write_text(
            """
[slotscheck]
strict-imports = true
include-modules = false
""",
            encoding="utf-8",
        )
        with pytest.raises(
            InvalidValueType,
            match=re.escape("Invalid value type for 'include-modules'."),
        ):
            PartialConfig.from_ini(Path(tmpdir / "setup.cfg"))


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
    assert bool(re.search(DEFAULT_MODULE_EXCLUDE_RE, string)) is expect
