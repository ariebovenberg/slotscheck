"Slots-related checks and inspection tools"
from typing import Collection, Iterator, Optional, Mapping
from inspect import isabstract as _is_abstract
from abc import ABC


def slots(c: type) -> Optional[Collection[str]]:
    """Get the __slots__ defined on a class."""
    try:
        slots_raw = c.__dict__["__slots__"]
    except KeyError:
        return None
    if isinstance(slots_raw, str):
        return (slots_raw,)
    elif isinstance(slots_raw, Iterator):
        raise NotImplementedError("Iterator __slots__ not supported. See #22")
    else:
        # We know it's a collection of strings now, since class creation
        # would have failed otherwise
        return slots_raw  # type: ignore[no-any-return]


def defines_slots(c: type) -> bool:
    """Whether a class defines __slots__."""
    # Checking c.__slots__ wouldn't work, since it might take it from
    # a base class.
    return "__slots__" in c.__dict__


def _all_static_attrs(c: type) -> Iterator[str]:
    for ancestor in c.__mro__:
        # NOTE: this only works on Python 3.13+, but the CLI should guard
        # against its use.
        try:
            yield from ancestor.__dataclass_fields__
            continue
        except AttributeError:
            pass
        # attrs classes store field info in __attrs_attrs__
        try:
            yield from (a.name for a in ancestor.__attrs_attrs__)
            continue
        except (AttributeError, TypeError):
            pass
        yield from getattr(ancestor, "__static_attributes__", ())


_IGNORED_SLOTS = frozenset({"__weakref__", "__dict__"})


def unused_slots(c: type) -> Mapping[str, type]:
    slots_by_class = {
        k: v
        for k, v in _slots_by_class(c)
        if k not in _IGNORED_SLOTS
    }
    for attr in _all_static_attrs(c):
        slots_by_class.pop(attr, None)
    return slots_by_class


def is_abstract(c: type) -> bool:
    return _is_abstract(c) or ABC in c.__bases__


def _slots_by_class(c: type) -> Iterator[tuple[str, type]]:
    """Get all slots defined on a class and its ancestors."""
    for ancestor in reversed(c.__mro__):
        for slot in slots(ancestor) or ():
            yield slot, ancestor


def _all_slots(c: type) -> Iterator[str]:
    """Get all slots defined on a class and its ancestors."""
    for ancestor in reversed(c.__mro__):
        yield from slots(ancestor) or ()


def has_implicit_dunder_dict(c: type) -> bool:
    return c.__dictoffset__ != 0 and "__dict__" not in _all_slots(c)


def causes_dunder_dict(c: type) -> bool:
    """Check if this type is the "cause" of a __dict__ being created."""
    return not defines_slots(c) and has_implicit_dunder_dict(c)


def slots_overlap(c: type) -> bool:
    """Check whether slots of this class overlap with any of its ancestors."""
    maybe_slots = slots(c)
    if maybe_slots is None:
        return False
    slots_ = set(maybe_slots)
    for ancestor in c.__mro__[1:]:
        if not slots_.isdisjoint(slots(ancestor) or ()):
            return True
    return False


def has_duplicate_slots(c: type) -> bool:
    slots_ = slots(c) or ()
    return len(set(slots_)) != len(list(slots_))
