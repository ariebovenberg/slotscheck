from abc import ABC
from typing import Generic, Protocol, TypeVar

from typing_extensions import Protocol as TypingExtProtocol
from typing_extensions import TypedDict as MyTypingExtensionsTypedDict


try:
    from typing import TypedDict

    class MyTypedDict(TypedDict):
        pass

except ImportError:
    pass


class MyTypedDictExc(MyTypingExtensionsTypedDict):
    pass


class A:
    pass


class B:
    __slots__ = ()


class C(B):
    pass


class D(C):
    pass


class E(B):
    __slots__ = ("a", "b")

    def __init__(self, a, b) -> None:
        self.a = a
        self.b = b


class F(E):
    __slots__ = ()


class G(F):
    __slots__ = ("k", "j")

    def __init__(self, k, j) -> None:
        self.k = k
        self.j = j


class H:
    __slots__ = {"k": "something", "z": "else"}

    def __init__(self, k, z) -> None:
        self.k = k
        self.z = z


class J(H):
    __slots__ = ["j", "a"]


class K(H):
    __slots__ = {"j", "a"}


class L(D):
    pass


class M(zip):
    __slots__ = ()


class N(zip):
    __slots__ = ("a", "b")


class P(int):
    __slots__ = ()


class Q(B, H):
    __slots__ = ("w",)


class R(Q):
    pass


class S(R):
    __slots__ = ()


class U(L):
    __slots__ = ("o", "p")

    class Ua(Q):
        __slots__ = ("i", "w")

    class Ub(Ua):
        __slots__ = "w"


class T(A):
    __slots__ = {"z", "r"}


class V(U):
    __slots__ = ("v",)


class W(V):
    __slots__ = {"p": "", "q": "", "v": ""}


class X(RuntimeError):
    pass


class Y(Exception):
    __slots__ = ("a", "b", "c")


class Z:
    __slots__ = ("a", "b", "c", "b", "b", "c")


class Za(Z):
    __slots__ = ("b", "c")


class MyProto(Protocol):
    pass


class ProtoWithSlots(Protocol):
    __slots__ = ("proto_slot",)


class MyOtherProto(TypingExtProtocol):
    pass


class SubProto(MyProto):
    pass


class Zb(MyProto):
    __slots__ = ()


Tvar = TypeVar("Tvar")


class Zc(Generic[Tvar]):
    __slots__ = ()


class Zd:
    __slots__ = ("a", "b", "__dict__")


class Ze(Zd):
    pass


class Zf(Zd):
    __slots__ = ("c", "d")


class UnusedSlotsClass:
    __slots__ = ("used", "unused_one", "unused_two")

    def __init__(self) -> None:
        self.used = 1


class AllSlotsUsed:
    __slots__ = ("x", "y")

    def __init__(self) -> None:
        self.x = 1
        self.y = 2


class AbstractWithSlots(ABC):
    __slots__ = ("abstract_slot",)


class ConcreteFromAbstract(AbstractWithSlots):
    __slots__ = ()

    def __init__(self) -> None:
        self.abstract_slot = 1
