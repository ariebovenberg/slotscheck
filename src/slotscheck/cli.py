from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import partial
from itertools import chain, filterfalse
from operator import attrgetter, not_
from pathlib import Path
from textwrap import indent
from typing import Any, Collection, Iterable, Iterator, List, Tuple, Union

import click

from . import config
from .checks import (
    has_slotless_base,
    has_slots,
    is_purepython_class,
    slots_overlap,
)
from .common import compose, flatten, groupby
from .discovery import (
    FailedImport,
    ModuleNotPurePython,
    ModuleTree,
    module_tree,
    walk_classes,
)


@click.command("slotscheck")
@click.argument("modulename")
@click.option(
    "--strict-imports/--no-strict-imports",
    help="Treat failed imports as errors.",
    default=None,
    show_default="not strict",
)
@click.option(
    "--require-superclass/--no-require-superclass",
    help="Report an error when a slots class inherits from "
    "a non-slotted class.",
    default=None,
    show_default="required",
)
@click.option(
    "--require-subclass/--no-require-subclass",
    help="Report an error when a non-slotted class inherits from "
    "a slotted class.",
    default=None,
    show_default="not required",
)
@click.option(
    "--include-modules",
    help="A regular expression that matches modules to include. "
    "Exclusions are determined first, then inclusions. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
)
@click.option(
    "--exclude-modules",
    help="A regular expression that matches modules to exclude. "
    "Excluded modules will not be imported. "
    "The root module will always be imported. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
    show_default=f"``{config.DEFAULT_MODULE_EXCLUDE_RE}``",
)
@click.option(
    "--include-classes",
    help="A regular expression that matches classes to include. "
    "Use ``:`` to separate module and class paths. "
    "For example: ``app`\\.config:.*Settings``, ``.*:.*(Foo|Bar)``. "
    "Exclusions are determined first, then inclusions. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
)
@click.option(
    "--exclude-classes",
    help="A regular expression that matches classes to exclude. "
    "Use ``:`` to separate module and class paths. "
    "For example: ``app\\.config:Settings``, ``.*:.*(Exception|Error)``. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Display extra descriptive output."
)
@click.version_option()
def root(
    modulename: str,
    verbose: bool,
    **kwargs: Any,
) -> None:
    "Check the ``__slots__`` definitions in a module."
    options = config.collect(kwargs, Path.cwd())
    classes, modules = collect(
        modulename, options.include_modules, options.exclude_modules
    )
    messages = list(
        chain(
            map(
                partial(Message, error=options.strict_imports),
                sorted(modules.skipped, key=attrgetter("name")),
            ),
            _check_classes(
                classes,
                options.require_superclass,
                options.include_classes,
                options.exclude_classes,
                options.require_subclass,
            ),
        )
    )
    for msg in messages:
        print(msg.for_display(verbose))

    if verbose:
        _print_report(modules, classes)

    if any_errors(messages):
        print("Oh no, found some problems!")
        exit(1)
    else:
        print("All OK!")


def _print_report(
    modules: ModuleReport,
    classes: Collection[type],
) -> None:
    classes_by_status = groupby(
        classes,
        key=lambda c: None
        if not is_purepython_class(c)
        else True
        if has_slots(c)
        else False,
    )
    print(
        """\
stats:
  modules:     {}
    checked:   {}
    excluded:  {}
    skipped:   {}

  classes:     {}
    has slots: {}
    no slots:  {}
    n/a:       {}
""".format(
            len(modules.all),
            len(modules.checked),
            len(modules.all) - len(modules.checked),
            len(modules.skipped),
            len(classes),
            len(classes_by_status[True]),
            len(classes_by_status[False]),
            len(classes_by_status[None]),
        ),
        file=sys.stderr,
    )


@dataclass(frozen=True)
class ModuleReport:
    all: ModuleTree
    checked: ModuleTree
    skipped: Collection[ModuleSkipped]


def _check_classes(
    classes: Iterable[type],
    require_superclass: bool,
    include: str | None,
    exclude: str | None,
    require_subclass: bool,
) -> Iterator[Message]:
    return map(
        partial(Message, error=True),
        flatten(
            map(
                partial(
                    slot_messages,
                    require_subclass=require_subclass,
                    require_superclass=require_superclass,
                ),
                sorted(
                    _class_includes(
                        _class_excludes(classes, exclude),
                        include,
                    ),
                    key=_class_fullname,
                ),
            )
        ),
    )


def _collect_modules(
    name: str, exclude: str, include: str | None
) -> Tuple[ModuleTree, ModuleTree]:
    """Collect and filter modules,
    returning the pruned tree and the number of original modules"""
    tree = discover(name)
    pruned = tree.filtername(
        compose(not_, re.compile(exclude, flags=re.VERBOSE).fullmatch)
    )
    return (
        pruned.filtername(
            compose(bool, re.compile(include, flags=re.VERBOSE).fullmatch)
        )
        if include
        else pruned
    ), tree


def _class_excludes(
    classes: Iterable[type], exclude: str | None
) -> Iterable[type]:
    return (
        filter(
            compose(
                not_,
                re.compile(exclude, flags=re.VERBOSE).fullmatch,
                _class_fullname,
            ),
            classes,
        )
        if exclude
        else classes
    )


def _class_includes(
    classes: Iterable[type], include: str | None
) -> Iterable[type]:
    return (
        filter(
            compose(
                re.compile(include, flags=re.VERBOSE).fullmatch,
                _class_fullname,
            ),
            classes,
        )
        if include
        else classes
    )


def discover(modulename: str) -> ModuleTree:
    try:
        return module_tree(modulename)
    except ModuleNotFoundError:
        print(_format_error(f"Module '{modulename}' not found."))
        exit(2)
    except ModuleNotPurePython:
        print(
            _format_error(
                f"Module '{modulename}' cannot be inspected. "
                "Is it an extension module?"
            )
        )
        exit(2)


def collect(
    modulename: str, include: str | None, exclude: str
) -> Tuple[Collection[type], ModuleReport]:
    pruned, original_tree = _collect_modules(modulename, exclude, include)
    classes, skipped = _extract_classes(pruned)
    return classes, ModuleReport(
        original_tree,
        pruned,
        skipped,
    )


def _extract_classes(
    tree: ModuleTree,
) -> Tuple[Collection[type], Collection[ModuleSkipped]]:
    classes: List[type] = []
    skipped: List[ModuleSkipped] = []
    for result in walk_classes(tree):
        if isinstance(result, FailedImport):
            skipped.append(ModuleSkipped(result.module, result.exc))
        else:
            classes.extend(result)
    return classes, skipped


@dataclass(frozen=True)
class ModuleSkipped:
    name: str
    exc: BaseException

    def for_display(self, verbose: bool) -> str:
        return (
            f"Failed to import '{self.name}'."
            + verbose * f"\nDue to {self.exc!r}"
        )


@dataclass(frozen=True)
class OverlappingSlots:
    cls: type

    def for_display(self, verbose: bool) -> str:
        return (
            f"'{_class_fullname(self.cls)}' defines overlapping slots."
            + verbose
            * (
                "\n"
                + _bulletlist(
                    f"{name} ({_class_fullname(base)})"
                    for name, base in sorted(_overlapping_slots(self.cls))
                )
            )
        )


def _overlapping_slots(c: type) -> Iterable[Tuple[str, type]]:
    slots = set(c.__dict__["__slots__"])
    for base in c.mro()[1:]:
        for overlap in slots.intersection(base.__dict__.get("__slots__", ())):
            yield (overlap, base)


@dataclass(frozen=True)
class BadSlotInheritance:
    cls: type

    def for_display(self, verbose: bool) -> str:
        return (
            f"'{_class_fullname(self.cls)}' has slots "
            "but superclass does not."
            + verbose
            * ("\n" + _class_bulletlist(_slotless_superclasses(self.cls)))
        )


@dataclass(frozen=True)
class ShouldHaveSlots:
    cls: type

    def for_display(self, verbose: bool) -> str:
        return (
            f"'{_class_fullname(self.cls)}' has no slots but superclass does."
        )


Notice = Union[
    ModuleSkipped, OverlappingSlots, BadSlotInheritance, ShouldHaveSlots
]


@dataclass(frozen=True)
class Message:
    notice: Notice
    error: bool

    def for_display(self, verbose: bool) -> str:
        return (_format_error if self.error else _format_note)(
            self.notice.for_display(verbose)
        )


def any_errors(ms: Iterable[Message]) -> bool:
    return any(m.error for m in ms)


def slot_messages(
    c: type, require_superclass: bool, require_subclass: bool
) -> Iterable[Notice]:
    if slots_overlap(c):
        yield OverlappingSlots(c)
    if require_superclass and has_slots(c) and has_slotless_base(c):
        yield BadSlotInheritance(c)
    elif require_subclass and not has_slots(c) and not has_slotless_base(c):
        yield ShouldHaveSlots(c)


_ERROR_PREFIX = "ERROR: "
_NOTE_PREFIX = "NOTE:  "


def _format_error(msg: str) -> str:
    return (
        _ERROR_PREFIX
        + indent(msg, " " * len(_ERROR_PREFIX))[len(_ERROR_PREFIX) :]  # noqa
    )


def _format_note(msg: str) -> str:
    return (
        _NOTE_PREFIX
        + indent(msg, " " * len(_NOTE_PREFIX))[len(_NOTE_PREFIX) :]  # noqa
    )


def _class_fullname(k: type) -> str:
    return f"{k.__module__}:{k.__qualname__}"


def _class_bulletlist(cs: Iterable[type]) -> str:
    return _bulletlist(map(_class_fullname, cs))


def _bulletlist(s: Iterable[str]) -> str:
    return "\n".join(map("- {}".format, s))


def _slotless_superclasses(c: type) -> Iterable[type]:
    return filterfalse(has_slots, c.mro())
