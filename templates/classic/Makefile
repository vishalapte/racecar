# templates/classic/Makefile — copy to project root (no rename needed).
# Classic variant using black + isort + pylint.
# `make check` is the canonical verification entry point.

# Auto-detect venv (order: .venv, venv, ../venv). If found, prepend its
# bin/ to PATH so black, isort, pylint, mypy, pytest, lint-imports,
# pre-commit resolve to the venv rather than system binaries.
VENV := $(firstword $(wildcard .venv venv ../venv))
ifdef VENV
  export PATH := $(abspath $(VENV))/bin:$(PATH)
endif

.PHONY: check fix fmt fmt-check lint test typecheck arch clean help

check: fmt-check lint test typecheck arch

fix: fmt

fmt:
	black src
	isort src

fmt-check:
	black --check src
	isort --check-only src

lint:
	pylint src
	pre-commit run no-upward-imports-in-business-modules --all-files

test:
	pytest

typecheck:
	mypy src

arch:
	lint-imports

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +

help:
	@echo "make check     - run all verification (fmt-check + lint + test + typecheck + arch)"
	@echo "make fix       - auto-fix formatting (black + isort)"
	@echo "make fmt       - format code in place"
	@echo "make fmt-check - check formatting without modifying"
	@echo "make lint      - pylint + custom arch-coherence/PYTHON.md §1 check"
	@echo "make test      - pytest"
	@echo "make typecheck - mypy"
	@echo "make arch      - lint-imports (DAG check)"
	@echo "make clean     - remove cache dirs"
