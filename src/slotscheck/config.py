"Logic for gathering and managing the configuration settings"

from dataclasses import dataclass, fields
from itertools import chain
from pathlib import Path
from typing import Any, ClassVar, Collection, Mapping, Optional, Type, TypeVar

import tomli

from .common import add_slots

RegexStr = str
"A regex string in Python's verbose syntax"
DEFAULT_MODULE_EXCLUDE_RE = r"(^|\.)__main__(\.|$)"
_T = TypeVar("_T")


@add_slots
@dataclass(frozen=True)
class PartialConfig:
    "Options given by user. Some may be missing."
    strict_imports: Optional[bool]
    require_subclass: Optional[bool]
    require_superclass: Optional[bool]
    include_modules: Optional[RegexStr]
    exclude_modules: Optional[RegexStr]
    include_classes: Optional[RegexStr]
    exclude_classes: Optional[RegexStr]

    EMPTY: ClassVar["PartialConfig"]

    @staticmethod
    def from_toml(p: Path) -> "PartialConfig":
        "May raise TOMLDecodeError or ValidationError. File must exist."
        with p.open("rb") as rfile:
            root = tomli.load(rfile)

        conf = root.get("tool", {}).get("slotscheck", {})
        if not conf.keys() <= _ALLOWED_KEYS.keys():
            raise InvalidKeys(conf.keys() - _ALLOWED_KEYS)

        return PartialConfig(
            **{
                key.replace("-", "_"): _extract_value(conf, key, expect_type)
                for key, expect_type in _ALLOWED_KEYS.items()
            },
        )


PartialConfig.EMPTY = PartialConfig(None, None, None, None, None, None, None)


@dataclass(frozen=True)
class Config(PartialConfig):
    __slots__ = ()
    strict_imports: bool
    require_subclass: bool
    require_superclass: bool
    exclude_modules: RegexStr

    DEFAULT: ClassVar["Config"]

    def apply(self, other: PartialConfig) -> "Config":
        return Config(
            **{
                f.name: _none_or(getattr(other, f.name), getattr(self, f.name))
                for f in fields(PartialConfig)
            }
        )


Config.DEFAULT = Config(
    strict_imports=False,
    require_subclass=False,
    require_superclass=True,
    include_modules=None,
    exclude_modules=DEFAULT_MODULE_EXCLUDE_RE,
    include_classes=None,
    exclude_classes=None,
)


def collect(cli_kwargs: Mapping[str, Any], cwd: Path) -> Config:
    tomlpath = find_pyproject_toml(cwd)
    toml_conf = (
        PartialConfig.from_toml(tomlpath) if tomlpath else PartialConfig.EMPTY
    )
    return Config.DEFAULT.apply(toml_conf).apply(PartialConfig(**cli_kwargs))


def find_pyproject_toml(path: Path) -> Optional[Path]:
    for p in chain((path,), path.parents):
        if (p / "pyproject.toml").is_file():
            return p / "pyproject.toml"
    else:
        return None


class InvalidKeys(Exception):
    def __init__(self, keys: Collection[str]) -> None:
        self.keys = keys

    def __str__(self) -> str:
        return (
            "Invalid configuration key(s): "
            + ", ".join(map("'{}'".format, sorted(self.keys)))
            + "."
        )


class InvalidValueType(Exception):
    def __init__(self, key: str) -> None:
        self.key = key

    def __str__(self) -> str:
        return f"Invalid value type for '{self.key}'."


def _none_or(a: Optional[_T], b: _T) -> _T:
    return b if a is None else a


def _extract_value(
    c: Mapping[str, object], key: str, expect_type: Type[_T]
) -> Optional[_T]:
    try:
        raw_value = c[key]
    except KeyError:
        return None
    else:
        if isinstance(raw_value, expect_type):
            return raw_value
        else:
            raise InvalidValueType(key)


_ALLOWED_KEYS = {
    "strict-imports": bool,
    "require-subclass": bool,
    "require-superclass": bool,
    "include-modules": str,
    "exclude-modules": str,
    "include-classes": str,
    "exclude-classes": str,
}
