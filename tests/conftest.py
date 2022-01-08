import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent / "examples"


@pytest.fixture(scope="session", autouse=True)
def add_pypath():
    "Add example modules to the python path"
    sys.path.insert(0, str(EXAMPLES_DIR))
    yield
    sys.path.remove(str(EXAMPLES_DIR))
