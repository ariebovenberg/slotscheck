"Tools to discover and inspect modules, packages, and classes"

import importlib
import pkgutil
import sys
from dataclasses import dataclass, field, replace
from functools import partial, reduce
from importlib.util import find_spec
from inspect import isclass
from itertools import chain
from pathlib import Path
from textwrap import indent
from types import ModuleType
from typing import (
    Callable,
    Collection,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    NamedTuple,
    Optional,
    Union,
)

from .common import add_slots, flatten, unique

ModuleName = str
"The full, dotted name of a module"

ModuleNamePart = str
"Part of a module name -- no dots"

ModuleTree = Union["Module", "Package"]

AbsPath = Path
"A resolved filepath. Contains no '..'."


def consolidate(trees: Iterable[ModuleTree]) -> Collection[ModuleTree]:
    "Deduplicate and merge module trees"
    seen: Dict[ModuleNamePart, ModuleTree] = {}
    for t in trees:
        try:
            overlap = seen[t.name]
        except KeyError:
            seen[t.name] = t
        else:
            seen[t.name] = overlap.merge(t)

    return seen.values()


@add_slots
@dataclass(frozen=True)
class Module:
    name: ModuleNamePart

    def __post_init__(self) -> None:
        assert "." not in self.name

    def display(self) -> str:
        return self.name

    def __iter__(self) -> Iterator[ModuleTree]:
        yield self

    def __len__(self) -> int:
        return 1

    def filtername(
        self, __pred: Callable[[ModuleName], bool], *, prefix: str = ""
    ) -> Optional[ModuleTree]:
        return self if __pred(prefix + self.name) else None

    def merge(self, other: ModuleTree) -> ModuleTree:
        "Merge along shared components. Raises if no shared components."
        if other.name == self.name:
            return other
        raise ValueError("Cannot merge modules without shared components.")


@add_slots
@dataclass(frozen=True)
class Package:
    name: ModuleNamePart
    content: FrozenSet[ModuleTree]

    def __post_init__(self) -> None:
        assert "." not in self.name

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
    ) -> Optional[ModuleTree]:
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

    def merge(self, other: ModuleTree) -> ModuleTree:
        "Merge along shared components. Raises if no shared components."
        if self.name != other.name:
            raise ValueError("Cannot merge modules without shared components.")
        if isinstance(other, Module):
            return self
        else:
            return Package(
                self.name,
                frozenset(consolidate(chain(self.content, other.content))),
            )


@dataclass(frozen=True)
class UnexpectedImportLocation(Exception):
    module: ModuleName
    expected: AbsPath
    actual: Optional[AbsPath]


@add_slots
@dataclass(frozen=True)
class FailedImport:
    module: ModuleName
    exc: BaseException = field(compare=False, hash=False)


def module_tree(
    module: ModuleName,
    expected_location: Optional[AbsPath],
) -> Union[ModuleTree, FailedImport]:
    """May raise ModuleNotFoundError or UnexpectedImportLocation"""
    try:
        spec = find_spec(module)
    except BaseException as e:
        return FailedImport(module, e)
    if spec is None:
        raise ModuleNotFoundError(f"No module named '{module}'", name=module)
    *namespaces, name = module.split(".")
    location = Path(spec.origin) if spec.has_location and spec.origin else None
    tree: ModuleTree
    if spec.submodule_search_locations is None:
        tree = Module(name)
    else:
        assert len(spec.submodule_search_locations) == 1
        pkg_location = Path(spec.submodule_search_locations[0])
        location = location or pkg_location
        tree = _package(name, pkg_location)

    if expected_location and location != expected_location:
        raise UnexpectedImportLocation(module, expected_location, location)

    return reduce(_add_namespace, reversed(namespaces), tree)


def _add_namespace(tree: ModuleTree, name: ModuleNamePart) -> ModuleTree:
    return Package(name, frozenset([tree]))


def _submodule(m: pkgutil.ModuleInfo) -> ModuleTree:
    if m.ispkg:
        [subdir] = m.module_finder.find_spec(
            m.name  # type: ignore
        ).submodule_search_locations
        return _package(m.name, Path(subdir))
    else:
        return Module(m.name)


def _is_submodule(m: pkgutil.ModuleInfo, path: AbsPath) -> bool:
    return getattr(m.module_finder, "path", "").startswith(str(path))


def _package(name: ModuleNamePart, path: AbsPath) -> Package:
    return Package(
        name,
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
) -> Iterator[Union[FailedImport, FrozenSet[type]]]:
    fullname = prefix + n.name
    try:
        module = importlib.import_module(fullname)
    except BaseException as e:
        # Sometimes packages make it impossible to import
        # certain modules directly or out of order, or without
        # some system or dependency requirement.
        # The exceptions can be quite exotic,
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


def _is_module_class(obj: object, module: ModuleType) -> bool:
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


def _is_nested_class(obj: object, parent: type) -> bool:
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


class ModuleLocated(NamedTuple):
    name: ModuleName
    expected_location: Optional[AbsPath]


def _is_module(p: AbsPath) -> bool:
    return (p.is_file() and p.suffixes == [".py"]) or _is_package(p)


def _is_package(p: AbsPath) -> bool:
    return p.is_dir() and (p / _INIT_PY).is_file()


def _module_parents(
    p: AbsPath, sys_path: FrozenSet[AbsPath]
) -> Iterable[AbsPath]:
    yield p
    for pp in p.parents:
        if pp in sys_path:
            return
        yield pp
    raise ValueError(f"File {p} is outside of PYTHONPATH ({sys.path})")


def _find_modules(
    p: AbsPath, sys_path: FrozenSet[AbsPath]
) -> Iterable[ModuleLocated]:
    if p.name == _INIT_PY:
        yield from _find_modules(p.parent, sys_path)
    elif _is_module(p):
        parents = list(_module_parents(p, sys_path))
        yield ModuleLocated(
            ".".join(p.stem for p in reversed(parents)),
            (p / _INIT_PY if _is_package(p) else p),
        )
    elif p.is_dir():
        yield from flatten(_find_modules(cp, sys_path) for cp in p.iterdir())


def find_modules(p: AbsPath) -> Iterable[ModuleLocated]:
    "Recursively find modules at given path. Nonexistent Path is ignored"
    return _find_modules(p, frozenset(map(Path, sys.path)))
