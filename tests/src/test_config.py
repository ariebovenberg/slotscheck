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
    find_config_file,
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


class TestFindConfigFile:
    def test_working_directory_toml(self, tmpdir):
        workdir, parentdir = tmpdir.ensure_dir("foo"), tmpdir
        (parentdir / "pyproject.toml").write_binary(EXAMPLE_TOML)
        (parentdir / "setup.cfg").write_binary(EXAMPLE_INI.encode())
        (workdir / "pyproject.toml").write_binary(EXAMPLE_TOML)
        (workdir / "setup.cfg").write_binary(EXAMPLE_INI.encode())
        assert find_config_file(Path(workdir)) == Path(
            workdir / "pyproject.toml"
        )

    def test_working_directory_cfg(self, tmpdir):
        workdir, parentdir = tmpdir.ensure_dir("foo"), tmpdir
        (parentdir / "pyproject.toml").write_binary(EXAMPLE_TOML)
        (parentdir / "setup.cfg").write_binary(EXAMPLE_INI.encode())
        (workdir / "pyproject.toml").write_binary(b"[foo]\nbar = 5")
        (workdir / "setup.cfg").write_binary(EXAMPLE_INI.encode())
        assert find_config_file(Path(workdir)) == Path(workdir / "setup.cfg")

    def test_not_found(self, tmpdir):
        (tmpdir / "pyproject.toml").write_binary(b"[foo]\nbar = 5")
        (tmpdir / "setup.cfg").write_binary(b"[foo]\nbar = 5")
        assert find_config_file(Path(tmpdir)) is None

    def test_parent_directory_toml(self, tmpdir):
        workdir, parentdir = tmpdir.ensure_dir("foo"), tmpdir
        (parentdir / "pyproject.toml").write_binary(EXAMPLE_TOML)
        (parentdir / "setup.cfg").write_binary(EXAMPLE_INI.encode())
        (workdir / "pyproject.toml").write_binary(b"[foo]\nbar = 5")
        (workdir / "setup.cfg").write_binary(b"[foo]\nbar = 5")
        assert find_config_file(Path(workdir)) == Path(
            parentdir / "pyproject.toml"
        )

    def test_parent_directory_cfg(self, tmpdir):
        workdir, parentdir = tmpdir.ensure_dir("foo"), tmpdir
        (parentdir / "setup.cfg").write_binary(EXAMPLE_INI.encode())
        (workdir / "pyproject.toml").write_binary(b"[foo]\nbar = 5")
        (workdir / "setup.cfg").write_binary(b"[foo]\nbar = 5")
        assert find_config_file(Path(workdir)) == Path(parentdir / "setup.cfg")


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
        Config = PartialConfig.load(Path(tmpdir / "myconf.toml"))
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
            PartialConfig.load(Path(tmpdir / "myconf.toml"))

    def test_no_slotscheck_section(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(
            b"""
[tool.bla]
k = 5
"""
        )
        assert PartialConfig.load(
            Path(tmpdir / "myconf.toml")
        ) == PartialConfig(None, None, None, None, None, None, None)

    def test_empty_slotscheck_section(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(
            b"""
[tool.slotscheck]
"""
        )
        assert PartialConfig.load(
            Path(tmpdir / "myconf.toml")
        ) == PartialConfig(None, None, None, None, None, None, None)

    def test_empty(self, tmpdir):
        (tmpdir / "myconf.toml").write_binary(b"")
        assert PartialConfig.load(
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
            PartialConfig.load(Path(tmpdir / "myconf.toml"))

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
            PartialConfig.load(Path(tmpdir / "myconf.toml"))


class TestPartialOptionsFromIni:
    def test_options_from_ini(self, tmpdir):
        (tmpdir / "setup.cfg").write_text(EXAMPLE_INI, encoding="utf-8")
        Config = PartialConfig.load(Path(tmpdir / "setup.cfg"))
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
        assert PartialConfig.load(Path(tmpdir / "setup.cfg")) == PartialConfig(
            None, None, None, None, None, None, None
        )

    def test_empty_slotscheck_section(self, tmpdir):
        (tmpdir / "myconf.toml").write_text(
            """
[slotscheck]
""",
            encoding="utf-8",
        )
        assert PartialConfig.load(Path(tmpdir / "setup.cfg")) == PartialConfig(
            None, None, None, None, None, None, None
        )

    def test_empty(self, tmpdir):
        (tmpdir / "setup.cfg").write_text("", encoding="utf-8")
        assert PartialConfig.load(Path(tmpdir / "setup.cfg")) == PartialConfig(
            None, None, None, None, None, None, None
        )

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
            PartialConfig.load(Path(tmpdir / "setup.cfg"))

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
            PartialConfig.load(Path(tmpdir / "setup.cfg"))


def test_config_from_file_invalid_extension():
    with pytest.raises(ValueError, match="extension.*toml"):
        PartialConfig.load(Path("foo.py"))


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
