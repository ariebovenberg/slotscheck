"A collection of evil objects that crash on introspection"


class Q:
    def __get__(self, *args) -> None:
        raise RuntimeError("BOOM!")


class W:
    R = Q()


class Z:
    @property
    def __class__(self) -> type:
        raise RuntimeError("BOOM!")

    @property
    def __module__(self) -> type:
        raise RuntimeError("BOOM!")


z = Z()


W.boom = Z()


def __getattr__(name):
    raise RuntimeError(f"BOOM: {name}")
