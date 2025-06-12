"Slots-related checks and inspection tools"
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
        # We know it's a collection of strings now, since class creation
        # would have failed otherwise
        return slots_raw  # type: ignore[no-any-return]


def defines_slots(c: type) -> bool:
    """Whether a class defines __slots__."""
    # Checking c.__slots__ wouldn't work, since it might take it from a base class.
    return "__slots__" in c.__dict__


def _has_slot(c: type, name: str) -> bool:
    for ancestor in c.__mro__:
        if name in (slots(ancestor) or ()):
            return True
    return False


def has_implicit_dunder_dict(c: type) -> bool:
    return c.__dictoffset__ != 0 and not _has_slot(c, "__dict__")


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
