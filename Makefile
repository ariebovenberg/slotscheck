.PHONY: init clean format fix lint type-check pytest check test docs

init:
	uv sync --locked --all-groups

clean:
	rm -rf .coverage .hypothesis .mypy_cache .pytest_cache .ruff_cache *.egg-info
	rm -rf dist
	find . | grep -E "(__pycache__|docs_.*$$|\.pyc|\.pyo$$)" | xargs rm -rf

format:
	uv run ruff format .

fix:
	uv run ruff check --select I --fix .
	uv run ruff format .

lint:
	uv run ruff check .

type-check:
	uv run mypy --pretty src tests/src

check: lint type-check

pytest:
	uv run pytest --cov=slotscheck

test: check pytest

docs:
	@touch docs/cli.rst
	uv run make -C docs/ html
