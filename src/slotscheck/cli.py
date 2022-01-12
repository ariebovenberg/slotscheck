from __future__ import annotations

import enum
import re
import sys
from dataclasses import dataclass
from functools import partial
from itertools import chain, filterfalse
from operator import attrgetter, not_
from textwrap import indent
from typing import Collection, Iterable, Iterator, List, Sequence, Tuple, Union

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
    "--disallow-nonslot-base/--allow-nonslot-base",
    help="Report an error when a slots class inherits from a nonslot class.",
    default=True,
    show_default="disallow",
)
@click.option(
    "--require-slots",
    type=click.Choice(["always", "subclass", "no"]),
    help="Require slots to be present always, "
    "when subclassing a slotted class, or to not require it.",
    default="no",
    show_default="no",
)
@click.option(
    "--include-modules",
    help="A regular expression that matches modules to include. "
    "Exclusions are determined first, then inclusions. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
    show_default="include all",
)
@click.option(
    "--exclude-modules",
    help="A regular expression that matches modules to exclude. "
    "Excluded modules will not be imported. "
    "The root module will always be imported. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
    default=DEFAULT_EXCLUDE_RE,
    show_default=DEFAULT_EXCLUDE_RE,
)
@click.option(
    "--include-classes",
    help="A regular expression that matches classes to include. "
    "Use `:` to separate module and class paths. "
    "For example: `app\\.config:.*Settings`, `.*:.*(Foo|Bar)`. "
    "Exclusions are determined first, then inclusions. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
    show_default="include all",
)
@click.option(
    "--exclude-classes",
    help="A regular expression that matches classes to exclude. "
    "Use `:` to separate module and class paths. "
    "For example: `app\\.config:Settings`, `.*:.*(Exception|Error)`. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Display extra descriptive output."
)
@click.version_option()
def root(
    modulename: str,
    strict_imports: bool,
    disallow_nonslot_base: bool,
    require_slots: str,
    include_modules: str | None,
    exclude_modules: str,
    include_classes: str | None,
    exclude_classes: str | None,
    verbose: bool,
) -> None:
    "Check the __slots__ definitions in a module."
    slots_requirement = RequireSlots[require_slots.upper()]
    tree, original_count = _collect_modules(
        modulename, exclude_modules, include_modules
    )
    classes, modules_skipped = extract_classes(tree)
    messages = list(
        chain(
            map(
                partial(Message, error=strict_imports),
                sorted(modules_skipped, key=attrgetter("name")),
            ),
            _check_classes(
                classes,
                disallow_nonslot_base,
                include_classes,
                exclude_classes,
                slots_requirement,
            ),
        )
    )
    for msg in messages:
        print(msg.for_display(verbose))

    if verbose:
        _print_report(
            ModuleReport(
                original_count,
                len(tree),
                original_count - len(tree),
                len(modules_skipped),
            ),
            classes,
        )

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
            modules.all,
            modules.checked,
            modules.excluded,
            modules.skipped,
            len(classes),
            len(classes_by_status[True]),
            len(classes_by_status[False]),
            len(classes_by_status[None]),
        ),
        file=sys.stderr,
    )


@dataclass(frozen=True)
class ModuleReport:
    all: int
    checked: int
    excluded: int
    skipped: int


def _check_classes(
    classes: Iterable[type],
    disallow_nonslot_base: bool,
    include: str | None,
    exclude: str | None,
    slots_requirement: RequireSlots,
) -> Iterator[Message]:
    return map(
        partial(Message, error=True),
        flatten(
            map(
                partial(
                    slot_messages,
                    slots_requirement=slots_requirement,
                    disallow_nonslot_base=disallow_nonslot_base,
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


@enum.unique
class RequireSlots(enum.Enum):
    ALWAYS = enum.auto()
    SUBCLASS = enum.auto()
    NO = enum.auto()


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


@dataclass(frozen=True)
class ShouldHaveSlots:
    cls: type

    def for_display(self, verbose: bool) -> str:
        return f"'{_class_fullname(self.cls)}' has no slots (required)."


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
    c: type, disallow_nonslot_base: bool, slots_requirement: RequireSlots
) -> Iterable[Notice]:
    if slots_overlap(c):
        yield OverlappingSlots(c)
    if disallow_nonslot_base and has_slots(c) and has_slotless_base(c):
        yield BadSlotInheritance(c)
    elif slots_requirement is RequireSlots.ALWAYS and not has_slots(c):
        yield ShouldHaveSlots(c)
    elif (
        slots_requirement is RequireSlots.SUBCLASS
        and not has_slots(c)
        and not has_slotless_base(c)
    ):
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
