import subprocess
import sys
from pathlib import Path

import pytest

import slotscheck


def test_version_is_lazy():
    source = Path(__file__).parents[2] / "src"
    code = f"""\
import builtins
import sys

sys.path.insert(0, {str(source)!r})
real_import = builtins.__import__
imports = []

def track_import(name, *args, **kwargs):
    imports.append(name)
    return real_import(name, *args, **kwargs)

builtins.__import__ = track_import
import slotscheck
assert "importlib.metadata" not in imports
assert slotscheck.__version__
assert "importlib.metadata" in imports
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_unknown_attribute():
    with pytest.raises(
        AttributeError,
        match="module 'slotscheck' has no attribute 'unknown'",
    ):
        slotscheck.unknown
