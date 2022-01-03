import enum
import importlib
import inspect
import logging
import pkgutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from types import ModuleType
from typing import (
    Callable,
    Collection,
    FrozenSet,
    Iterable,
    Iterator,
    Mapping,
    TypeVar,
)

import click

T1 = TypeVar("T1")
T2 = TypeVar("T2")

logger = logging.getLogger(__name__)

# Single-sourcing the version number with poetry:
# https://github.com/python-poetry/poetry/pull/2366#issuecomment-652418094
try:
    __version__ = __import__("importlib.metadata").metadata.version(__name__)
except ModuleNotFoundError:  # pragma: no cover
    __version__ = __import__("importlib_metadata").version(__name__)


@enum.unique
class SlotsStatus(enum.Enum):
    NO_SLOTS = enum.auto()
    HAS_SLOTS = enum.auto()
    NOT_PUREPYTHON = enum.auto()


def _all_bases_have_slots(c: type) -> bool:
    return all(slot_status(b) is not SlotsStatus.NO_SLOTS for b in c.__bases__)


def walk_classes(module: ModuleType) -> Iterator[type]:
    yield from (
        klass
        for _, klass in inspect.getmembers(module, inspect.isclass)
        if klass.__module__.startswith(module.__name__)
    )
    try:
        module_path = module.__path__[0]  # type: ignore
    except (AttributeError, IndexError):
        return  # it's not a package with submodules

    packages = pkgutil.walk_packages([module_path])
    for finder, name, _ in packages:
        if not getattr(finder, "path", "").startswith(module_path):
            continue

        module_name = f"{module.__name__}.{name}"
        try:
            next_module = importlib.import_module(module_name)
        except BaseException as e:
            # sometimes packages make it impossible to import
            # certain modules directly or out of order, or without
            # some system or dependency requirement.
            logger.warning("Couldn't import %s. (%r)", module_name, e)
        else:
            yield from walk_classes(next_module)


def slot_status(c: type) -> SlotsStatus:
    if "__slots__" in c.__dict__:
        return SlotsStatus.HAS_SLOTS
    elif _is_purepython_class(c):
        return SlotsStatus.NO_SLOTS
    else:
        return SlotsStatus.NOT_PUREPYTHON


def _class_fullname(k: type) -> str:
    return f"{k.__module__}.{k.__qualname__}"


def _is_purepython_class(t: type) -> bool:
    "whether a class is defined in Python, or an extension/C module"
    # There is no easy way to check if a class is pure Python.
    # One symptom of a non-native class is that it is not possible to
    # set attributes on it. Let's do that.
    try:
        t._SLOTSCHECK_POKE = 1  # type: ignore
    except TypeError as e:
        if e.args[0].startswith(
            "cannot set '_SLOTSCHECK_POKE' attribute of immutable type"
        ):
            return False
        raise  # some other error we may want to know about
    else:
        del t._SLOTSCHECK_POKE  # type: ignore
        return True


def _groupby(
    it: Iterable[T1], key: Callable[[T1], T2]
) -> Mapping[T2, Collection[T1]]:
    grouped = defaultdict(list)
    for i in it:
        grouped[key(i)].append(i)

    return grouped


@dataclass(frozen=True)
class BrokenSlots:
    cls: type
    bases: FrozenSet[type]


@click.command()
@click.version_option()
@click.argument("modulename")
@click.option("-v", "--verbose", is_flag=True)
def cli(modulename: str, verbose: bool) -> None:
    "Report the __slots__ definitions of classes in a package."
    logging.basicConfig(
        format="LOG: %(message)s",
        stream=sys.stderr,
        level=logging.INFO if verbose else logging.ERROR,
    )
    classes = _groupby(
        sorted(
            set(walk_classes(importlib.import_module(modulename))),
            key=_class_fullname,
        ),
        key=slot_status,
    )
    broken_slots = [
        (
            c,
            sorted(
                filter(
                    lambda b: slot_status(b) is SlotsStatus.NO_SLOTS,
                    c.mro(),
                ),
                key=_class_fullname,
            ),
        )
        for c in classes[SlotsStatus.HAS_SLOTS]
        if not _all_bases_have_slots(c)
    ]
    if broken_slots:
        for klass, slotless_bases in broken_slots:
            print(
                f"ERROR: '{_class_fullname(klass)}' has slots but "
                "inherits from non-slot class"
            )
            if verbose:
                for cls in slotless_bases:
                    print(f"       - {_class_fullname(cls)}")
        exit(1)
    else:
        print(
            """\
All OK!
Classes scanned:
  with slots:              {}
  without slots:           {}
""".format(
                len(classes[SlotsStatus.HAS_SLOTS]),
                len(classes[SlotsStatus.NO_SLOTS]),
            )
        )
