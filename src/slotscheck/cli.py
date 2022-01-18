from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import partial
from itertools import chain, filterfalse
from operator import attrgetter, itemgetter, methodcaller, not_
from pathlib import Path
from textwrap import indent
from typing import (
    Any,
    Collection,
    Iterable,
    Iterator,
    List,
    Sequence,
    Tuple,
    Union,
)

import click

from . import config
from .checks import (
    has_slotless_base,
    has_slots,
    is_purepython_class,
    slots_overlap,
)
from .common import (
    Predicate,
    add_slots,
    both,
    compose,
    flatten,
    groupby,
    map_optional,
)
from .discovery import (
    FailedImport,
    ModuleName,
    ModuleNotPurePython,
    ModuleTree,
    consolidate,
    find_modules,
    module_tree,
    walk_classes,
)


@click.command("slotscheck")
@click.argument(
    "FILES",
    type=click.Path(path_type=Path, exists=True, resolve_path=True),
    required=False,
    nargs=-1,
)
@click.option(
    "-m",
    "--module",
    help="Check this module. Cannot be combined with FILES argument. "
    "Can be repeated multiple times to scan several modules. ",
    multiple=True,
)
@click.option(
    "--strict-imports/--no-strict-imports",
    help="Treat failed imports as errors.",
    default=True,
    show_default="strict",
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
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
    show_default=f"``{config.DEFAULT_MODULE_EXCLUDE_RE}``",
)
@click.option(
    "--include-classes",
    help="A regular expression that matches classes to include. "
    "Use ``:`` to separate module and class paths. "
    "For example: ``app\\.config:.*Settings``, ``:(Foo|Bar)``. "
    "Exclusions are determined first, then inclusions. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
)
@click.option(
    "--exclude-classes",
    help="A regular expression that matches classes to exclude. "
    "Use ``:`` to separate module and class paths. "
    "For example: ``app\\.config:Settings``, ``:.*(Exception|Error)``. "
    "Uses Python's verbose regex dialect, so whitespace is mostly ignored.",
    show_default="^$",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Display extra descriptive output."
)
@click.version_option()
def root(
    files: Sequence[Path],
    module: Sequence[str],
    verbose: bool,
    **kwargs: Any,
) -> None:
    "Check whether your __slots__ are working properly."
    conf = config.collect(kwargs, Path.cwd())
    if not (files or module):
        print("No files or modules given. Nothing to do!")
        exit(0)

    try:
        classes, modules = _collect(files, module, conf)
    except ModuleNotFoundError as e:
        print(_format_error(f"Module '{e.name}' not found."))
        exit(1)
    except ModuleNotPurePython as e:
        print(
            _format_error(
                f"Module '{e.name}' cannot be inspected. "
                "Is it an extension module?"
            )
        )
        exit(1)

    if not modules.filtered:
        print(
            "Files or modules given, but filtered out by exclude/include. "
            "Nothing to do!"
        )
        exit(0)
    messages = list(
        chain(
            map(
                partial(Message, error=conf.strict_imports),
                sorted(modules.skipped, key=attrgetter("failure.module")),
            ),
            _check_classes(
                classes,
                conf.require_superclass,
                conf.include_classes,
                conf.exclude_classes,
                conf.require_subclass,
            ),
        )
    )
    for msg in messages:
        print(msg.for_display(verbose))

    any_errors = any(m.error for m in messages)

    if any_errors:
        print("Oh no, found some problems!")
    else:
        print("All OK!")

    if verbose:
        _print_report(
            modules,
            classes,
        )
    else:
        print(
            f"Scanned {sum(map(len, modules.filtered))} module(s), "
            f"{len(classes)} class(es)."
        )

    if any_errors:
        exit(1)


def _collect(
    files: Collection[Path],
    modules: Collection[ModuleName],
    conf: config.Config,
) -> Tuple[Collection[type], ModulesReport]:
    modulefilter = _create_filter(conf.include_modules, conf.exclude_modules)
    modules_all = consolidate(
        map(module_tree, filter(modulefilter, _as_modules(files, modules)))
    )
    modules_filtered: Collection[ModuleTree] = list(
        map_optional(methodcaller("filtername", modulefilter), modules_all)
    )
    classes, modules_skipped = _collect_classes(modules_filtered)
    return classes, ModulesReport(
        modules_all,
        modules_filtered,
        modules_skipped,
    )


def _create_filter(include: str | None, exclude: str) -> Predicate[str]:
    excluder: Predicate[str] = compose(
        not_, re.compile(exclude, flags=re.VERBOSE).search
    )
    return (
        excluder
        if include is None
        else both(excluder, re.compile(include, flags=re.VERBOSE).search)
    )


def _as_modules(
    files: Collection[Path], names: Collection[ModuleName]
) -> Collection[ModuleName]:
    if files and names:
        print(
            _format_error(
                "Specify either FILES argument or `-m/--module` "
                "option, not both."
            ),
            file=sys.stderr,
        )
        exit(2)
    elif files:
        return [m.name for m in flatten(map(find_modules, files))]
    else:
        return names


def _collect_classes(
    trees: Collection[ModuleTree],
) -> Tuple[Collection[type], Collection[ModuleSkipped]]:
    classes: List[type] = []
    skipped: List[ModuleSkipped] = []
    for result in flatten(map(walk_classes, trees)):
        if isinstance(result, FailedImport):
            skipped.append(ModuleSkipped(result))
        else:
            classes.extend(result)
    return classes, skipped


def _print_report(
    modules: ModulesReport,
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
    n/a:       {}""".format(
            sum(map(len, modules.all)),
            sum(map(len, modules.filtered)),
            sum(map(len, modules.all)) - sum(map(len, modules.filtered)),
            len(modules.skipped),
            len(classes),
            len(classes_by_status[True]),
            len(classes_by_status[False]),
            len(classes_by_status[None]),
        ),
        file=sys.stderr,
    )


@add_slots
@dataclass(frozen=True)
class ModulesReport:
    all: Collection[ModuleTree]
    filtered: Collection[ModuleTree]
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


def _class_excludes(
    classes: Iterable[type], exclude: str | None
) -> Iterable[type]:
    return (
        filter(
            compose(
                not_,
                re.compile(exclude, flags=re.VERBOSE).search,
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
                re.compile(include, flags=re.VERBOSE).search,
                _class_fullname,
            ),
            classes,
        )
        if include
        else classes
    )


@add_slots
@dataclass(frozen=True)
class ModuleSkipped:
    failure: FailedImport

    def for_display(self, verbose: bool) -> str:
        return (
            f"Failed to import '{self.failure.module}'."
            + verbose * f"\nDue to {self.failure.exc!r}"
        )


@add_slots
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
                    for name, base in sorted(
                        _overlapping_slots(self.cls), key=itemgetter(0)
                    )
                )
            )
        )


def _overlapping_slots(c: type) -> Iterable[Tuple[str, type]]:
    slots = set(c.__dict__["__slots__"])
    for base in c.mro()[1:]:
        for overlap in slots.intersection(base.__dict__.get("__slots__", ())):
            yield (overlap, base)


@add_slots
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


@add_slots
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


@add_slots
@dataclass(frozen=True)
class Message:
    notice: Notice
    error: bool

    def for_display(self, verbose: bool) -> str:
        return (_format_error if self.error else _format_note)(
            self.notice.for_display(verbose)
        )


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
