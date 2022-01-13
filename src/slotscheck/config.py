from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any, ClassVar, Collection, Mapping, Type, TypeVar

import tomli

T = TypeVar("T")

RegexStr = str
"A regex string in Python's verbose syntax"

DEFAULT_MODULE_EXCLUDE_RE = r"(\w*\.)*__main__(\.\w*)*"


def collect(cli_kwargs: Mapping[str, Any], cwd: Path) -> Options:
    tomlpath = find_pyproject_toml(cwd)
    return (
        Options.DEFAULT.combine(PartialOptions.from_toml(tomlpath))
        if tomlpath
        else Options.DEFAULT
    ).combine(PartialOptions(**cli_kwargs))


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


@dataclass(frozen=True)
class PartialOptions:
    "Options given by user. Some may be missing"
    strict_imports: bool | None
    require_subclass: bool | None
    require_superclass: bool | None
    include_modules: RegexStr | None
    exclude_modules: RegexStr | None
    include_classes: RegexStr | None
    exclude_classes: RegexStr | None

    @staticmethod
    def from_toml(p: Path) -> PartialOptions:
        "May raise TOMLDecodeError or ValidationError"
        with p.open("rb") as rfile:
            root = tomli.load(rfile)

        conf = root.get("tool", {}).get("slotscheck", {})
        if not conf.keys() <= _ALLOWED_KEYS.keys():
            raise InvalidKeys(conf.keys() - _ALLOWED_KEYS)

        return PartialOptions(
            **{
                key.replace("-", "_"): _extract_value(conf, key, expect_type)
                for key, expect_type in _ALLOWED_KEYS.items()
            },
        )


@dataclass(frozen=True)
class Options(PartialOptions):
    strict_imports: bool
    require_subclass: bool
    require_superclass: bool
    exclude_modules: RegexStr

    DEFAULT: ClassVar[Options]

    def combine(self, other: PartialOptions) -> Options:
        return Options(
            **{
                n: _none_or(getattr(other, n), getattr(self, n))
                for n in PartialOptions.__dataclass_fields__
            }
        )


Options.DEFAULT = Options(
    strict_imports=False,
    require_subclass=False,
    require_superclass=True,
    include_modules=None,
    exclude_modules=DEFAULT_MODULE_EXCLUDE_RE,
    include_classes=None,
    exclude_classes=None,
)


def _none_or(a: T | None, b: T) -> T:
    return b if a is None else a


def _extract_value(
    c: Mapping[str, object], key: str, expect_type: Type[T]
) -> T | None:
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


def find_pyproject_toml(path: Path) -> Path | None:
    for p in chain((path,), path.parents):
        if (p / "pyproject.toml").is_file():
            return p / "pyproject.toml"
    else:
        return None
