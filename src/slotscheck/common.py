from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import chain, filterfalse
from typing import (
    Any,
    Callable,
    Collection,
    Iterable,
    Mapping,
    Set,
    Tuple,
    TypeVar,
)

flatten = chain.from_iterable


_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")


# adapted from itertools recipe
def unique(iterable: Iterable[_T1]) -> Iterable[_T1]:
    "List unique elements, preserving order."
    seen: Set[_T1] = set()
    seen_add = seen.add
    for element in filterfalse(seen.__contains__, iterable):
        seen_add(element)
        yield element


def groupby(
    it: Iterable[_T1], *, key: Callable[[_T1], _T2]
) -> Mapping[_T2, Collection[_T1]]:
    "Group items into a dict by key"
    grouped = defaultdict(list)
    for i in it:
        grouped[key(i)].append(i)

    return grouped


@dataclass(frozen=True, repr=False)
class compose:
    "Funtion composition"
    __slots__ = ("_functions",)
    _functions: Tuple[Callable[[Any], Any], ...]

    def __init__(self, *functions: Any) -> None:
        object.__setattr__(self, "_functions", functions)

    def __call__(self, value: Any) -> Any:
        for f in reversed(self._functions):
            value = f(value)
        return value
