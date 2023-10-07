.PHONY: clean isort isort-check format format-check fix lint type-check pytest check test documentation docs



init:
	poetry install
	pip install -r docs/requirements.txt

clean:
	rm -rf .coverage .hypothesis .mypy_cache .pytest_cache .tox *.egg-info
	rm -rf dist
	find . | grep -E "(__pycache__|docs_.*$$|\.pyc|\.pyo$$)" | xargs rm -rf

isort:
	isort src tests/src/

isort-check:
	isort . --check-only --diff

format:
	black src tests/src

format-check:
	black --check --diff .

fix: isort format

lint:
	flake8 src tests --exclude=.tox,build

type-check:
	mypy --pretty src tests/src

check: lint isort-check format-check type-check

pytest:
	pytest --cov=slotscheck

test: check pytest

docs:
	@touch docs/cli.rst
	make -C docs/ html
