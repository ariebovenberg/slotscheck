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


class F(E):
    __slots__ = ()


class G(F):
    __slots__ = ("k", "j")


class H:
    __slots__ = {"k": "something", "z": "else"}


class J(H):
    __slots__ = ["j", "a"]


class K(H):
    __slots__ = {"j", "a"}


class L(D):
    pass


class M(RuntimeError):
    __slots__ = ()


class N(RuntimeError):
    __slots__ = ("a", "b")


class P(int):
    __slots__ = ()


class Q(B, H):
    __slots__ = ("w",)


class R(Q):
    pass


S = R
