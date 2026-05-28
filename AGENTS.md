# AGENTS.md

Guide for AI agents working on the `slotscheck` codebase.

## Project Overview

`slotscheck` is a Python CLI tool that verifies `__slots__` are defined correctly
across class hierarchies. It imports modules, introspects classes, and reports
slot-related issues (overlaps, duplicates, missing slots in subclasses, etc.).

**Key constraint:** slotscheck works by *actually importing* the target code at
runtime—it is not a static analysis tool. This means import side-effects,
import ordering, and `sys.path` configuration are central concerns.

## Architecture

```
src/slotscheck/
├── __init__.py      # Package version (from importlib.metadata)
├── __main__.py      # `python -m slotscheck` entrypoint
├── cli.py           # Click CLI, orchestration, message/report formatting
├── checks.py        # Low-level slot introspection predicates
├── common.py        # Shared functional utilities and type helpers
├── config.py        # Configuration loading, merging, validation
└── discovery.py     # Module/package discovery and class extraction
```

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Entry point. Parses CLI args, loads config, discovers modules, runs checks, formats output. This is the orchestration hub. |
| `discovery.py` | Converts file paths or module names into importable module trees. Recursively imports packages, extracts classes (including nested), captures import failures. |
| `checks.py` | Pure introspection: determines if a class has slots, if slots overlap with parent classes, if slots are duplicated, and whether a class is pure Python vs C extension. |
| `config.py` | Loads settings from `pyproject.toml` or `setup.cfg`, merges with CLI flags, validates keys/types, provides defaults. |
| `common.py` | Generic helpers (`flatten`, `unique`, `groupby`, `compose`), type predicates (`is_protocol`, `is_typeddict`), and an `add_slots` dataclass decorator. |

### Data Flow

```
CLI args + config file
        │
        ▼
    config.collect()  →  Config
        │
        ▼
    discovery.find_modules() / discovery.module_tree()
        │
        ▼
    discovery.walk_classes()  →  classes + FailedImports
        │
        ▼
    checks (has_slots, slots_overlap, has_slotless_base, ...)
        │
        ▼
    cli: format notices/messages, print report, exit code
```

## Development

### Prerequisites

- Python 3.9+ (3.9–3.13 supported)
- [Poetry](https://python-poetry.org/) for dependency management
- [tox](https://tox.wiki/) for test automation

### Setup

```bash
poetry install
pip install -r docs/requirements.txt
```

### Common Commands

| Task | Command |
|------|---------|
| Run tests | `pytest --cov=slotscheck` or `tox` |
| Lint | `flake8 src tests --exclude=.tox,build` |
| Format | `black src tests/src` |
| Sort imports | `isort src tests/src/` |
| Type check | `mypy --pretty src tests/src` |
| All checks | `make test` (lint + format + isort + mypy + pytest) |
| Self-check | `slotscheck -m slotscheck --verbose` |
| Build docs | `tox -e docs` |

### Tox Environments

- Default: runs pytest with coverage
- `lint`: black --check + flake8
- `isort`: isort --check
- `mypy`: type checking
- `slots`: runs slotscheck on itself
- `docs`: Sphinx build (warns-as-errors)

### CI

GitHub Actions (`.github/workflows/build.yml`):
- Tests on Python 3.9–3.13
- Coverage uploaded to Codecov on Python 3.11
- Poetry lockfile consistency check

## Testing

### Structure

```
tests/
├── __init__.py          # exists for mypy overrides
├── src/
│   ├── conftest.py      # Shared fixtures (sys.path, import cleanup)
│   ├── test_checks.py   # Unit tests for checks.py
│   ├── test_config.py   # Config loading/merging/validation
│   ├── test_discovery.py # Module tree building, class extraction
│   └── test_cli.py      # End-to-end CLI tests via CliRunner
└── examples/            # Crafted packages for test scenarios
```

### Key Testing Patterns

- **`click.testing.CliRunner`** for CLI integration tests
- **`@pytest.mark.parametrize`** for table-driven tests
- **Autouse fixtures:**
  - `add_pypath()`: prepends example dirs to `sys.path`
  - `undo_examples_import()`: clears example modules from `sys.modules` after each test
  - `set_cwd()`: sets working directory to `tests/examples` for CLI tests
- **Example packages** in `tests/examples/` cover: valid slots, invalid slots,
  import failures, namespace packages, compiled modules, `__main__` handling

### Running a Single Test

```bash
pytest tests/src/test_cli.py::test_name -v
```

## Configuration

Slotscheck reads from `[tool.slotscheck]` in `pyproject.toml` or `[slotscheck]`
in `setup.cfg`. Key options:

| Option | Type | Description |
|--------|------|-------------|
| `strict-imports` | bool | Treat failed imports as errors |
| `require-superclass` | bool | Require slots on classes with slotted superclasses |
| `require-subclass` | bool | Require slots on subclasses of slotted classes |
| `include-modules` | regex | Only check matching module paths |
| `exclude-modules` | regex | Skip matching module paths |
| `include-classes` | regex | Only check matching class names |
| `exclude-classes` | regex | Skip matching class names |

Default exclusion: `__main__` modules are always excluded.

## Pre-commit Hook

Slotscheck provides a pre-commit hook (`.pre-commit-hooks.yaml`). Important:
the hook needs access to the project's dependencies since it imports code.
Using `language: system` (not `language: python`) is recommended so the hook
runs in the project's own environment.

## Style & Conventions

- **Line length:** 79 characters (black + isort configured)
- **Import sorting:** isort with black profile
- **Type annotations:** fully typed (`py.typed` marker present), checked with mypy
- **Dataclasses with slots:** uses a custom `@add_slots` decorator from `common.py`
- **Functional style:** heavy use of iterators, `flatten`, `groupby`, `compose`
- **No runtime dependencies** beyond `click` and `tomli` (Python <3.11 only)
