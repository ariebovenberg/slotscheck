from array import array
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from random import Random
from xml.etree.ElementTree import Element

import pytest
from typing_extensions import TypedDict as TypingExtensionsTypedDict

from slotscheck.checks import (
    has_implicit_dunder_dict,
    slots_overlap,
)

try:
    from typing import TypedDict
except ImportError:
    TypedDict = TypingExtensionsTypedDict


class HasSlots:
    __slots__ = ("a", "b")


class NoSlots:
    pass


class GoodInherit(HasSlots):
    __slots__ = ["c", "d", "e"]


class BadOverlaps(GoodInherit):
    __slots__ = {"a": "some docstring", "f": "bla"}


class NoSlotsInherits(HasSlots):
    pass


class BadInherit(Random):
    __slots__ = ()


class BadInheritAndOverlap(NoSlotsInherits):
    __slots__ = ["z", "b", "a"]


class ChildOfBadClass(BadInheritAndOverlap):
    pass


class _RestrictiveMeta(type):
    def __setattr__(self, name, value) -> None:
        raise TypeError("BOOM!")


class MetaClass(type):
    pass


class MetaClassSlots(type):
    __slots__ = ()


class _UnsettableClass(metaclass=_RestrictiveMeta):
    pass


class OneStringSlot(HasSlots):
    __slots__ = "baz"


class ArrayInherit(array):  # type: ignore[type-arg]
    __slots__ = ()


class FooMeta(type):
    __slots__ = ()


class Foo(metaclass=FooMeta):
    __slots__ = ()


class MyDict(TypedDict):
    foo: str


class MyTypingExtensionsTypedDict(TypingExtensionsTypedDict):
    bla: int


class MyException(Exception):
    pass


class DunderDictSlot:
    __slots__ = ("a", "b", "__dict__")


class DunderDictSlotExtra(HasSlots):
    __slots__ = ("c", "d", "__dict__")


class InheritDunderDictSlot(DunderDictSlot):
    pass


class ExtendDunderDictSlot(DunderDictSlot):
    __slots__ = ("x",)


class MyEnum(Enum):
    A = 1
    B = 2


class TestHasImplicitDunderDict:
    @pytest.mark.parametrize(
        "klass, expect",
        [
            (type, True),
            (dict, False),
            (date, False),
            (float, False),
            (Decimal, False),
            (Element, False),
            (Exception, True),
            (array, False),
        ],
    )
    def test_not_purepython(self, klass, expect):
        assert has_implicit_dunder_dict(klass) is expect

    def test_typeddict(self):
        # This is a bit of a strange case
        # but the errors in the end work out (see cli.py)
        assert has_implicit_dunder_dict(MyDict)
        assert has_implicit_dunder_dict(MyTypingExtensionsTypedDict)

    def test_metaclass(self):
        assert has_implicit_dunder_dict(MetaClass)
        assert has_implicit_dunder_dict(MetaClassSlots)

    @pytest.mark.parametrize(
        "klass, expect",
        [
            (Fraction, False),
            (HasSlots, False),
            (GoodInherit, False),
            (BadInherit, True),
            (BadOverlaps, False),
            (OneStringSlot, False),
            (ArrayInherit, False),
            (Foo, False),
            (FooMeta, True),
        ],
    )
    def test_slots(self, klass, expect):
        assert has_implicit_dunder_dict(klass) is expect

    @pytest.mark.parametrize(
        "klass",
        [
            Random,
            Enum,
            NoSlotsInherits,
            ChildOfBadClass,
            RuntimeError,
            KeyboardInterrupt,
            MyException,
            MyEnum,
        ],
    )
    def test_no_slots(self, klass):
        assert has_implicit_dunder_dict(klass)

    def test_immutable_class(self):
        assert has_implicit_dunder_dict(_UnsettableClass)

    def test_explicit_dunder_dict(self):
        assert not has_implicit_dunder_dict(DunderDictSlot)
        assert not has_implicit_dunder_dict(DunderDictSlotExtra)
        assert not has_implicit_dunder_dict(InheritDunderDictSlot)
        assert not has_implicit_dunder_dict(ExtendDunderDictSlot)


class TestSlotsOverlap:
    @pytest.mark.parametrize(
        "klass",
        [type, dict, date, float, Decimal, AssertionError, RuntimeError],
    )
    def test_not_purepython(self, klass):
        assert not slots_overlap(klass)

    @pytest.mark.parametrize(
        "klass",
        [
            Fraction,
            HasSlots,
            GoodInherit,
            BadInherit,
            OneStringSlot,
            Foo,
            FooMeta,
            ArrayInherit,
        ],
    )
    def test_slots_ok(self, klass):
        assert not slots_overlap(klass)

    @pytest.mark.parametrize("klass", [BadOverlaps, BadInheritAndOverlap])
    def test_slots_not_ok(self, klass):
        assert slots_overlap(klass)

    @pytest.mark.parametrize(
        "klass", [Random, Enum, NoSlotsInherits, ChildOfBadClass]
    )
    def test_no_slots(self, klass):
        assert not slots_overlap(klass)
