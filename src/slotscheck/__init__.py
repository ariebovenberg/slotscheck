import importlib
import inspect
import pkgutil
import sys
from itertools import filterfalse
from typing import Any, Iterator

import click

# Single-sourcing the version number with poetry:
# https://github.com/python-poetry/poetry/pull/2366#issuecomment-652418094
try:
    __version__ = __import__("importlib.metadata").metadata.version(__name__)
except ModuleNotFoundError:  # pragma: no cover
    __version__ = __import__("importlib_metadata").version(__name__)


def _classes_in_module(module: Any, verbose: bool) -> Iterator[type]:
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
                importlib.import_module(module_name), verbose
            )
        except BaseException as e:
            # sometimes packages make it impossible to import
            # certain modules directly or out of order, or without
            # some system or dependency requirement.
            if verbose:
                click.secho(
                    f"Couldn't import {module_name} ({e.__class__.__name__}).",
                    err=True,
                    fg="cyan",
                )


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
@click.option("-v", "--verbose", is_flag=True)
def cli(module: str, verbose: bool) -> None:
    classes_with_broken_slots = [
        (k, list(filterfalse(_has_slots, k.__bases__)))
        for k in _classes_in_module(
            importlib.import_module(module), verbose=verbose
        )
        if _has_improper_slots(k)
    ]
    if classes_with_broken_slots:
        for klass, culprits in classes_with_broken_slots:
            click.secho(
                f"incomplete slots in '{_class_fullname(klass)}'",
                fg="yellow",
            )
            if verbose:
                for c in culprits:
                    click.secho(f"↳ {_class_fullname(c)}", fg="red", err=True)

        sys.exit(1)
    click.secho("All good!", fg="green", err=True)
