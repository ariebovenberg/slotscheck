"Slots-related checks and inspection tools"
import builtins
import sys
from functools import lru_cache
from typing import Collection, Iterator, Optional


def slots(c: type) -> Optional[Collection[str]]:
    try:
        slots_raw = c.__dict__["__slots__"]
    except KeyError:
        return None
    if isinstance(slots_raw, str):
        return (slots_raw,)
    elif isinstance(slots_raw, Iterator):
        raise NotImplementedError("Iterator __slots__ not supported. See #22")
    else:
        return slots_raw


def has_slots(c: type) -> bool:
    return (
        "__slots__" in c.__dict__
        or c in _SLOTTED_BUILTINS
        or (
            not issubclass(c, BaseException)
            and not is_purepython_class(c)  # type: ignore
        )
    )


def has_slotless_base(c: type) -> bool:
    return not all(map(has_slots, c.__bases__))


def slots_overlap(c: type) -> bool:
    maybe_slots = slots(c)
    if maybe_slots is None:
        return False
    slots_ = set(maybe_slots)
    for ancestor in c.mro()[1:]:
        if not slots_.isdisjoint(slots(ancestor) or ()):
            return True
    return False


def has_duplicate_slots(c: type) -> bool:
    slots_ = slots(c) or ()
    return len(set(slots_)) != len(list(slots_))


_SLOTTED_BUILTINS = {
    obj
    for obj in builtins.__dict__.values()
    if type(obj) is type and not issubclass(obj, BaseException)
}


_UNSETTABLE_ATTRITUBE_MSG = (
    "cannot set '_SLOTSCHECK_POKE' attribute of immutable type"
    if sys.version_info > (3, 10)
    else "can't set attributes of built-in/extension type"
)


@lru_cache(maxsize=None)
def is_purepython_class(t: type) -> bool:
    "Whether a class is defined in Python, or an extension/C module"
    # AFIAK there is no _easy_ way to check if a class is pure Python.
    # One symptom of a non-native class is that it is not possible to
    # set attributes on it.
    # Let's use that as an easy proxy for now.
    try:
        t._SLOTSCHECK_POKE = 1  # type: ignore
    except TypeError as e:
        if e.args[0].startswith(_UNSETTABLE_ATTRITUBE_MSG):
            return False
        raise  # some other error we may want to know about
    else:
        del t._SLOTSCHECK_POKE  # type: ignore
        return True
