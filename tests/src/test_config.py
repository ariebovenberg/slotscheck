import re
from pathlib import Path

import pytest
import tomli

from slotscheck.config import (
    DEFAULT_MODULE_EXCLUDE_RE,
    InvalidKeys,
    InvalidValueType,
    Config,
    PartialConfig,
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
    assert bool(re.fullmatch(DEFAULT_MODULE_EXCLUDE_RE, string)) is expect
