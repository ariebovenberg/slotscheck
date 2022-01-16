"Tools to discover and inspect modules, packages, and classes"
from __future__ import annotations

import importlib
import importlib.abc
import pkgutil
from dataclasses import dataclass, field, replace
from functools import partial
from inspect import isclass
from itertools import takewhile
from pathlib import Path
from textwrap import indent
from types import ModuleType
from typing import Any, Callable, FrozenSet, Iterable, Iterator, Union

from .common import add_slots, flatten, unique

ModuleName = str
"The full, dotted name of a module"


@add_slots
@dataclass(frozen=True)
class Module:
    name: str

    def display(self) -> str:
        return self.name

    def __iter__(self) -> Iterator[ModuleTree]:
        yield self

    def __len__(self) -> int:
        return 1

    def filtername(
        self, __pred: Callable[[ModuleName], bool], *, prefix: str = ""
    ) -> ModuleTree | None:
        return self if __pred(prefix + self.name) else None


@add_slots
@dataclass(frozen=True)
class Package:
    name: str
    content: FrozenSet[ModuleTree]

    def display(self) -> str:
        return (
            f"{self.name}"
            + ("\n" * bool(self.content))
            + "\n".join(
                indent(node.display(), " ")
                for node in sorted(
                    self.content, key=lambda n: (type(n) is Package, n.name)
                )
            )
        )

    def __iter__(self) -> Iterator[ModuleTree]:
        yield self
        yield from flatten(self.content)

    def __len__(self) -> int:
        return 1 + sum(map(len, self.content))

    def filtername(
        self, __pred: Callable[[ModuleName], bool], *, prefix: str = ""
    ) -> ModuleTree | None:
        if not __pred(prefix + self.name):
            return None

        new_prefix = f"{prefix}{self.name}."
        return replace(
            self,
            content=frozenset(
                filter(
                    None,
                    (
                        sub.filtername(__pred, prefix=new_prefix)
                        for sub in self.content
                    ),
                )
            ),
        )


ModuleTree = Union[Module, Package]


class ModuleNotPurePython(Exception):
    pass


def module_tree(module: str) -> ModuleTree:
    "May raise ModuleNotFound or ModuleNotPurePython"
    loader = pkgutil.get_loader(module)
    if loader is None:
        raise ModuleNotFoundError(name=module)
    elif not isinstance(loader, importlib.abc.FileLoader):
        raise ModuleNotPurePython()
    elif loader.is_package(module):
        assert isinstance(loader.path, str)
        return _package(module, Path(loader.path).parent)
    else:
        return Module(module)


def _submodule(m: pkgutil.ModuleInfo) -> ModuleTree:
    if m.ispkg:
        [subdir] = m.module_finder.find_spec(
            m.name  # type: ignore
        ).submodule_search_locations
        return _package(m.name, Path(subdir))
    else:
        return Module(m.name)


def _is_submodule(m: pkgutil.ModuleInfo, path: Path) -> bool:
    return getattr(m.module_finder, "path", "").startswith(str(path))


def _package(module: str, path: Path) -> Package:
    return Package(
        module,
        frozenset(
            map(
                _submodule,
                filter(
                    partial(_is_submodule, path=path),
                    pkgutil.walk_packages([str(path)]),
                ),
            )
        ),
    )


def walk_classes(
    n: ModuleTree, prefix: str = ""
) -> Iterator[FailedImport | FrozenSet[type]]:
    fullname = prefix + n.name
    try:
        module = importlib.import_module(fullname)
    except BaseException as e:
        # sometimes packages make it impossible to import
        # certain modules directly or out of order, or without
        # some system or dependency requirement.
        # The Exceptions can be quite exotic,
        # inheriting from BaseException in some cases!
        if isinstance(e, KeyboardInterrupt):
            raise
        yield FailedImport(fullname, e)
    else:
        yield frozenset(_classes_in_module(module))
        if isinstance(n, Package):
            yield from flatten(
                map(partial(walk_classes, prefix=fullname + "."), n.content)
            )


@add_slots
@dataclass(frozen=True)
class FailedImport:
    module: str
    exc: BaseException = field(compare=False, hash=False)


def _classes_in_module(module: ModuleType) -> Iterable[type]:
    return flatten(
        map(
            _walk_nested_classes,
            unique(
                filter(
                    partial(_is_module_class, module=module),
                    module.__dict__.values(),
                )
            ),
        )
    )


def _is_module_class(obj: Any, module: ModuleType) -> bool:
    try:
        return isclass(obj) and obj.__module__ == module.__name__
    except Exception:
        # Some rare objects crash on introspection. It's best to exclude them.
        return False


def _walk_nested_classes(c: type) -> Iterable[type]:
    yield c
    yield from flatten(map(_walk_nested_classes, _nested_classes(c)))


def _nested_classes(c: type) -> Iterable[type]:
    return unique(
        filter(partial(_is_nested_class, parent=c), c.__dict__.values())
    )


def _is_nested_class(obj: Any, parent: type) -> bool:
    try:
        return (
            isclass(obj)
            and obj.__module__ == parent.__module__
            and obj.__qualname__.startswith(parent.__name__ + ".")
        )
    except Exception:
        # Some rare objects crash on introspection. It's best to exclude them.
        return False


_INIT_PY = "__init__.py"


@dataclass(frozen=True)
class FoundModule:
    name: ModuleName
    location: Path


def _is_module(p: Path) -> bool:
    return (p.is_file() and p.suffixes == [".py"]) or _is_package(p)


def _is_package(p: Path) -> bool:
    return p.is_dir() and (p / _INIT_PY).is_file()


def find_modules(p: Path) -> Iterable[FoundModule]:
    "Recursively find modules at given Path. Nonexistent Path is ignored"
    if p.name == _INIT_PY:
        yield from find_modules(p.resolve().parent)
    elif _is_module(p):
        parents = [p] + list(takewhile(_is_package, p.resolve().parents))
        yield FoundModule(
            ".".join(p.stem for p in reversed(parents)), parents[-1].parent
        )
    elif p.is_dir():
        yield from flatten(map(find_modules, p.iterdir()))
