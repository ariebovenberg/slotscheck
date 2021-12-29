import importlib
import sys
from itertools import filterfalse
import click
import inspect
import pkgutil
from typing import Any, Iterator


# Single-sourcing the version number with poetry:
# https://github.com/python-poetry/poetry/pull/2366#issuecomment-652418094
try:
    __version__ = __import__("importlib.metadata").metadata.version(__name__)
except ModuleNotFoundError:  # pragma: no cover
    __version__ = __import__("importlib_metadata").version(__name__)


def _classes_in_module(module: Any) -> Iterator[type]:
    yield from (
        klass
        for _, klass in inspect.getmembers(module, inspect.isclass)
        if klass.__module__.startswith(module.__name__)
    )
    try:
        module_path = module.__path__[0]
    except (AttributeError, IndexError):
        return  # it's not a package with submodules

    packages = pkgutil.walk_packages([module_path])
    for finder, name, _ in packages:
        if not getattr(finder, "path", "").startswith(module_path):
            continue

        module_name = f"{module.__name__}.{name}"
        try:
            yield from _classes_in_module(
                importlib.import_module(module_name),
            )
        except BaseException as e:
            # sometimes packages make it impossible to import
            # certain modules directly or out of order, or without
            # some system or dependency requirement.
            print(f"Could not import {module_name} ({e.__class__.__name__}).")


_BUILTINS_WITH_SLOTS = (object, tuple)


def _has_slots(klass: type) -> bool:
    # note that hasattr(klass, '__dict__') wouldn't work!
    return "__slots__" in klass.__dict__ or klass in _BUILTINS_WITH_SLOTS


def _has_improper_slots(klass: type) -> bool:
    return _has_slots(klass) and not all(map(_has_slots, klass.__bases__))


def _class_fullname(k: type) -> str:
    return f"{k.__module__}.{k.__qualname__}"


@click.command()
@click.version_option()
@click.argument("module")
def cli(module: str):
    classes_with_broken_slots = [
        (k, list(filterfalse(_has_slots, k.__bases__)))
        for k in _classes_in_module(importlib.import_module(module))
        if _has_improper_slots(k)
    ]
    if classes_with_broken_slots:
        for klass, culprits in classes_with_broken_slots:
            click.secho(_class_fullname(klass), fg="yellow")
            for c in culprits:
                click.secho(f"↳ {_class_fullname(c)}", fg="red")

        sys.exit(1)
    click.secho(f"All good!", fg="green")
