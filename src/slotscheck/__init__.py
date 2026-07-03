__version__: str


def __getattr__(name: str) -> str:
    if name == "__version__":
        from importlib.metadata import version

        resolved = version(__name__)
        globals()[name] = resolved
        return resolved
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
