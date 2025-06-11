# Makefile for iceOS – high-level dev tasks

PYTHON := python
PIP := pip

.PHONY: help install lint type test refresh-docs doctor clean

help:
	@echo "Available targets:"
	@echo "  install        Install dependencies (core + [test] extras)"
	@echo "  lint           Run ruff and isort checks"
	@echo "  type           Run mypy static type checking"
	@echo "  test           Run pytest with coverage"
	@echo "  refresh-docs   Regenerate docs (catalog + overview)"
	@echo "  doctor         Run full healthcheck suite"
	@echo "  clean          Remove .pyc, build, and coverage artifacts"

install:
	$(PIP) install -e .[test]

lint:
	ruff check src
	isort --check-only src

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

clean:
	rm -rf .pytest_cache dist build *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} + 