# Makefile for iceOS – high-level dev tasks

PYTHON := python
PIP := pip

.PHONY: help install lint type test coverage mutation refresh-docs doctor clean docs

help:
	@echo "Available targets:"
	@echo "  install        Install dependencies (core + [test] extras)"
	@echo "  lint           Run ruff and isort checks"
	@echo "  type           Run mypy static type checking"
	@echo "  test           Run pytest with coverage"
	@echo "  coverage       Run pytest with branch coverage"
	@echo "  mutation       Run mutmut mutation testing"
	@echo "  refresh-docs   Regenerate docs (catalog + overview)"
	@echo "  doctor         Run full healthcheck suite"
	@echo "  clean          Remove .pyc, build, and coverage artifacts"
	@echo "  docs           Build documentation site (output to site/)"

install:
	$(PIP) install -e .[test]

lint:
	ruff check src
	isort --check-only src
	mypy src

format:
	black src scripts tests
	isort src scripts tests

type:
	mypy src

test:
	pytest -q

refresh-docs:
	$(PYTHON) scripts/gen_catalog.py
	$(PYTHON) scripts/gen_overview.py

doctor:
	$(PYTHON) scripts/doctor.py

coverage:
	pytest

mutation:
	mutmut run --paths-to-mutate src --tests-dir tests

clean:
	rm -rf .pytest_cache dist build *.egg-info
	rm -rf .coverage htmlcov .ruff_cache .mypy_cache .benchmarks .import_linter_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +

docs:
	mkdocs build -s 