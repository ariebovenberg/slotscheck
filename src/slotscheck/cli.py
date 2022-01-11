from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import partial
from itertools import chain, filterfalse
from operator import not_
from textwrap import indent
from typing import Iterable, List, Sequence, Tuple, Union

import click

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

DEFAULT_EXCLUDE_RE = r"(\w*\.)*__main__(\.\w*)*"


@click.command("slotscheck")
@click.argument("modulename")
@click.option(
    "--strict-imports", is_flag=True, help="Treat failed imports as errors."
)
@click.option(
    "--disallow-nonslot-inherit/--allow-nonslot-inherit",
    help="Report an error when a slots class inherits from a nonslot class.",
    default=True,
    show_default="disallow",
)
@click.option(
    "--exclude-classes",
    help="A regular expression that matches classes to exclude. "
    "Use `:` to separate module and class paths. "
    "For example: `app\\.config:Settings`, `.*?:.*(Exception|Error)`. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
)
@click.option(
    "--include-classes",
    help="A regular expression that matches classes to include. "
    "Use `:` to separate module and class paths. "
    "For example: `app\\.config:.*Settings`, `.*?:.*(Foo|Bar)`. "
    "Exclusions are determined first, then inclusions.",
    show_default="include all",
)
@click.option(
    "--exclude-modules",
    help="A regular expression that matches modules to exclude. "
    "Excluded modules will not be imported. "
    "The root module will always be imported. ",
    default=DEFAULT_EXCLUDE_RE,
    show_default=DEFAULT_EXCLUDE_RE,
)
@click.option(
    "--include-modules",
    help="A regular expression that matches modules to include. "
    "Exclusions are determined first, then inclusions.",
    show_default="include all",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Display extra descriptive output."
)
@click.version_option()
def root(
    modulename: str,
    verbose: bool,
    strict_imports: bool,
    disallow_nonslot_inherit: bool,
    include_modules: str | None,
    exclude_modules: str,
    include_classes: str | None,
    exclude_classes: str | None,
) -> None:
    "Check the __slots__ definitions in a module."
    tree, original_count = _collect_modules(
        modulename, exclude_modules, include_modules
    )
    classes, modules_skipped = extract_classes(tree)
    messages = list(
        chain(
            map(
                partial(Message, error=strict_imports),
                sorted(modules_skipped, key=lambda m: m.name),
            ),
            flatten(
                map(
                    partial(
                        slot_messages,
                        disallow_nonslot_inherit=disallow_nonslot_inherit,
                    ),
                    sorted(
                        _class_includes(
                            _class_excludes(classes, exclude_classes),
                            include_classes,
                        ),
                        key=_class_fullname,
                    ),
                )
            ),
        )
    )
    errors_found = any_errors(messages)
    for msg in messages:
        print(msg.for_display(verbose))

    if errors_found:
        print("Oh no, found some problems!")
    else:
        print("All OK!")

    if verbose:
        classes_by_status = groupby(
            classes,
            key=lambda c: None
            if not is_purepython_class(c)
            else True
            if has_slots(c)
            else False,
        )
        print(
            """
stats:
  modules:     {}
    checked:   {}
    excluded:  {}
    skipped:   {}

  classes:     {}
    has slots: {}
    no slots:  {}
    n/a:       {}""".format(
                original_count,
                len(tree),
                original_count - len(tree),
                len(modules_skipped),
                len(classes),
                len(classes_by_status[True]),
                len(classes_by_status[False]),
                len(classes_by_status[None]),
            ),
            file=sys.stderr,
        )

    if errors_found:
        exit(1)


def _collect_modules(
    name: str, exclude: str, include: str | None
) -> Tuple[ModuleTree, int]:
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
    ), len(tree)


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


def extract_classes(
    tree: ModuleTree,
) -> Tuple[Sequence[type], Sequence[ModuleSkipped]]:
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
            * ("\n" + _bulletlist(sorted(_overlapping_slots(self.cls))))
        )


def _overlapping_slots(c: type) -> Iterable[str]:
    slots = set(c.__dict__["__slots__"])
    for base in c.mro()[1:]:
        yield from slots.intersection(base.__dict__.get("__slots__", ()))


@dataclass(frozen=True)
class BadSlotInheritance:
    cls: type

    def for_display(self, verbose: bool) -> str:
        return (
            f"'{_class_fullname(self.cls)}' has slots "
            "but inherits from non-slot class."
            + verbose
            * ("\n" + _class_bulletlist(_slotless_superclasses(self.cls)))
        )


Notice = Union[ModuleSkipped, OverlappingSlots, BadSlotInheritance]


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
    c: type, disallow_nonslot_inherit: bool
) -> Iterable[Message]:
    if slots_overlap(c):
        yield Message(
            OverlappingSlots(c),
            error=True,
        )
    if disallow_nonslot_inherit and has_slots(c) and has_slotless_base(c):
        yield Message(BadSlotInheritance(c), error=True)


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
