from __future__ import annotations

from collections import defaultdict
from itertools import chain, filterfalse
from typing import Callable, Collection, Iterable, Mapping, Set, TypeVar

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
    grouped = defaultdict(list)
    for i in it:
        grouped[key(i)].append(i)

    return grouped
