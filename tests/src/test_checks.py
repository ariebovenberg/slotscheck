import sys
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
    is_abstract,
    slots,
    slots_overlap,
    unused_slots,
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


@pytest.mark.skipif(
    sys.version_info < (3, 13),
    reason="unused_slots requires __static_attributes__ (Python 3.13+)",
)
class TestUnusedSlots:
    def test_all_used(self):
        class AllUsed:
            __slots__ = ("a", "b")

            def __init__(self):
                self.a = 1
                self.b = 2

        assert unused_slots(AllUsed) == {}

    def test_some_unused(self):
        class SomeUnused:
            __slots__ = ("used", "unused_one", "unused_two")

            def __init__(self):
                self.used = 1

        result = unused_slots(SomeUnused)
        assert set(result.keys()) == {"unused_one", "unused_two"}

    def test_empty_slots(self):
        class Empty:
            __slots__ = ()

        assert unused_slots(Empty) == {}

    def test_inherited_usage(self):
        class Base:
            __slots__ = ("a",)

        class Child(Base):
            __slots__ = ("b",)

            def __init__(self):
                self.a = 1
                self.b = 2

        assert unused_slots(Child) == {}

    def test_inherited_unused(self):
        class Base:
            __slots__ = ("a",)

        class Child(Base):
            __slots__ = ("b",)

            def __init__(self):
                self.b = 2

        result = unused_slots(Child)
        assert set(result.keys()) == {"a"}

    def test_dunder_dict_excluded(self):
        class WithDunderDict:
            __slots__ = ("a", "__dict__")

            def __init__(self):
                self.a = 1

        assert unused_slots(WithDunderDict) == {}

    def test_weakref_excluded(self):
        class WithWeakref:
            __slots__ = ("a", "__weakref__")

            def __init__(self):
                self.a = 1

        assert unused_slots(WithWeakref) == {}

    def test_dataclass_fields(self):
        from dataclasses import dataclass

        @dataclass
        class DC:
            __slots__ = ("x", "y")
            x: int
            y: int

        assert unused_slots(DC) == {}

    def test_attrs_fields(self):
        import attr

        @attr.s(slots=True)
        class AttrsClass:
            x: int = attr.ib()
            y: int = attr.ib()

        assert unused_slots(AttrsClass) == {}


class TestIsAbstract:
    def test_abc_class(self):
        from abc import ABC, abstractmethod

        class MyABC(ABC):
            __slots__ = ("x",)

            @abstractmethod
            def method(self):
                pass

        assert is_abstract(MyABC)

    def test_abc_base(self):
        from abc import ABC

        class DirectABC(ABC):
            pass

        assert is_abstract(DirectABC)

    def test_not_abstract(self):
        assert not is_abstract(HasSlots)
        assert not is_abstract(NoSlots)

    def test_concrete_subclass_of_abc(self):
        from abc import ABC, abstractmethod

        class MyABC(ABC):
            __slots__ = ("x",)

            @abstractmethod
            def method(self):
                pass

        class Concrete(MyABC):
            __slots__ = ()

            def method(self):
                pass

        assert not is_abstract(Concrete)


def test_iterator_slots():

    class A:
        __slots__ = iter(("foo", "bar"))

    with pytest.raises(Exception, match="[Ii]terator"):
        slots(A)
