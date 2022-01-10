from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import partial
from itertools import chain, filterfalse
from textwrap import indent
from typing import Iterable, List, Sequence, Tuple, Union

import click

from .checks import (
    has_slotless_base,
    has_slots,
    is_purepython_class,
    slots_overlap,
)
from .common import flatten, groupby
from .discovery import (
    FailedImport,
    ModuleNotPurePython,
    ModuleTree,
    module_tree,
    walk_classes,
)

DEFAULT_EXCLUDE_RE = r"(.+\.)?__main__(\..+)?"


@click.command("slotscheck")
@click.argument("modulename")
@click.option(
    "--strict-imports", is_flag=True, help="Treat failed imports as errors."
)
@click.option(
    "--exclude",
    help="A regular expression that matches modules or classes to exclude. "
    "Use `:` to seperate module and class paths. "
    "Excluded modules (without `:`) will not be imported at all. "
    "The root module will always be imported. "
    "Examples: `.*foo.*`, `.*\\.api:(Settings|Config)`.",
    default=DEFAULT_EXCLUDE_RE,
    show_default=DEFAULT_EXCLUDE_RE,
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Display extra descriptive output."
)
@click.version_option()
def root(
    modulename: str, verbose: bool, strict_imports: bool, exclude: str
) -> None:
    "Check the __slots__ definitions in a module."
    exclude_re = re.compile(exclude)
    tree = discover(modulename)
    pruned = tree.filtername(lambda x: not exclude_re.fullmatch(x))
    classes, modules_skipped = extract_classes(pruned)
    messages = list(
        chain(
            map(
                partial(Message, error=strict_imports),
                sorted(modules_skipped, key=lambda m: m.name),
            ),
            flatten(
                map(
                    slot_messages,
                    sorted(
                        filter(
                            lambda c: not exclude_re.fullmatch(
                                _class_fullname(c)
                            ),
                            classes,
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
                len(tree),
                len(pruned) - len(modules_skipped),
                len(tree) - len(pruned),
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
    for result in walk_classes(tree, parent_name=None):
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


def slot_messages(c: type) -> Iterable[Message]:
    if slots_overlap(c):
        yield Message(
            OverlappingSlots(c),
            error=True,
        )
    if has_slots(c) and has_slotless_base(c):
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
