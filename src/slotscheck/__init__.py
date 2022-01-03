import enum
import importlib
import inspect
import logging
import pkgutil
import sys
from collections import defaultdict
from types import ModuleType
from typing import Callable, Collection, Iterable, Iterator, Mapping, TypeVar

import click

logger = logging.getLogger(__name__)

# Single-sourcing the version number with poetry:
# https://github.com/python-poetry/poetry/pull/2366#issuecomment-652418094
try:
    __version__ = __import__("importlib.metadata").metadata.version(__name__)
except ModuleNotFoundError:  # pragma: no cover
    __version__ = __import__("importlib_metadata").version(__name__)


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
    else:
        print("All OK!")

    if verbose:
        print(
            """
Classes scanned:
  with slots:      {}
  without slots:   {}
  non pure Python: {}""".format(
                len(classes[SlotsStatus.HAS_SLOTS]),
                len(classes[SlotsStatus.NO_SLOTS]),
                len(classes[SlotsStatus.NOT_PUREPYTHON]),
            ),
            file=sys.stderr,
        )

    if broken_slots:
        exit(1)


@enum.unique
class SlotsStatus(enum.Enum):
    NO_SLOTS = enum.auto()
    HAS_SLOTS = enum.auto()
    NOT_PUREPYTHON = enum.auto()


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


def _all_bases_have_slots(c: type) -> bool:
    return all(slot_status(b) is not SlotsStatus.NO_SLOTS for b in c.__bases__)


_UNSETTABLE_ATTRITUBE_MSG = (
    "cannot set '_SLOTSCHECK_POKE' attribute of immutable type"
    if sys.version_info > (3, 10)
    else "can't set attributes of built-in/extension type"
)


def _is_purepython_class(t: type) -> bool:
    "Whether a class is defined in Python, or an extension/C module"
    # There is no easy way to check if a class is pure Python.
    # One symptom of a non-native class is that it is not possible to
    # set attributes on it. Let's do that.
    try:
        t._SLOTSCHECK_POKE = 1  # type: ignore
    except TypeError as e:
        if e.args[0].startswith(_UNSETTABLE_ATTRITUBE_MSG):
            return False
        raise  # some other error we may want to know about
    else:
        del t._SLOTSCHECK_POKE  # type: ignore
        return True


_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")


def _groupby(
    it: Iterable[_T1], key: Callable[[_T1], _T2]
) -> Mapping[_T2, Collection[_T1]]:
    grouped = defaultdict(list)
    for i in it:
        grouped[key(i)].append(i)

    return grouped
