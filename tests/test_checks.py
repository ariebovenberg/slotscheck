from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from random import Random

import pytest

from slotscheck.checks import has_slotless_base, has_slots, slots_overlap


class HasSlots:
    __slots__ = ("a", "b")


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


class _UnsettableClass(metaclass=_RestrictiveMeta):
    pass


class TestHasSlots:
    @pytest.mark.parametrize(
        "klass",
        [type, dict, date, float, Decimal, AssertionError, RuntimeError],
    )
    def test_not_purepython(self, klass):
        assert has_slots(klass)

    @pytest.mark.parametrize(
        "klass", [Fraction, HasSlots, GoodInherit, BadInherit, BadOverlaps]
    )
    def test_slots(self, klass):
        assert has_slots(klass)

    @pytest.mark.parametrize(
        "klass", [Random, Enum, NoSlotsInherits, ChildOfBadClass]
    )
    def test_no_slots(self, klass):
        assert not has_slots(klass)

    def test_opaque_class(self):
        with pytest.raises(TypeError, match="BOOM!"):
            assert not has_slots(_UnsettableClass)


class TestSlotsOverlap:
    @pytest.mark.parametrize(
        "klass",
        [type, dict, date, float, Decimal, AssertionError, RuntimeError],
    )
    def test_not_purepython(self, klass):
        assert not slots_overlap(klass)

    @pytest.mark.parametrize(
        "klass", [Fraction, HasSlots, GoodInherit, BadInherit]
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


class TestHasSlotlessBase:
    @pytest.mark.parametrize(
        "klass",
        [type, dict, date, float, Decimal, AssertionError, RuntimeError],
    )
    def test_not_purepython(self, klass):
        assert not has_slotless_base(klass)

    @pytest.mark.parametrize(
        "klass", [Fraction, HasSlots, GoodInherit, BadOverlaps]
    )
    def test_slots_ok(self, klass):
        assert not has_slotless_base(klass)

    @pytest.mark.parametrize("klass", [BadInherit, BadInheritAndOverlap])
    def test_slots_not_ok(self, klass):
        assert has_slotless_base(klass)

    @pytest.mark.parametrize("klass", [Enum, NoSlotsInherits, ChildOfBadClass])
    def test_no_slots(self, klass):
        assert not has_slotless_base(klass)
