from typing import NamedTuple
from uuid import UUID


class A:
    pass


class B:
    def __init__(self) -> None:
        pass

    @property
    def foo(self) -> None:
        pass

    class C:
        def __init__(self) -> None:
            pass

        class D:
            pass

        K = A

        J = D

    F = C

    Z = UUID


class E(NamedTuple):
    r: float


B.Foo = B


Alias1 = B
Alias2 = B.C.D
Alias3 = UUID
Alias4 = Alias2
Alias5 = B.C.K
