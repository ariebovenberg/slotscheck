# Single-sourcing the version number with poetry:
# https://github.com/python-poetry/poetry/pull/2366#issuecomment-652418094
__version__ = __import__("importlib.metadata").metadata.version(__name__)
