# Single-source the version number from the installed distribution.
__version__ = __import__("importlib.metadata").metadata.version(__name__)
