# templates/ruff/Makefile — copy to project root (no rename needed).
# `make check` is the canonical verification entry point.

# Auto-detect venv (order: .venv, venv, ../venv). If found, prepend its
# bin/ to PATH so ruff, black, mypy, pytest, lint-imports, pre-commit
# resolve to the venv rather than system binaries.
VENV := $(firstword $(wildcard .venv venv ../venv))
ifdef VENV
  export PATH := $(abspath $(VENV))/bin:$(PATH)
endif

# Package path or dotted name to audit for architectural coherence.
# Override with:  make arch PKG=my_package
PKG ?= src

.PHONY: check fix fmt fmt-check lint test typecheck arch clean help

check: fmt-check lint test typecheck arch

fix: fmt

fmt:
	ruff check --fix src
	black src

fmt-check:
	ruff check src
	black --check src

lint:
	pre-commit run no-upward-imports-in-business-modules --all-files

test:
	pytest

typecheck:
	mypy src

arch:
	lint-imports
	python scripts/check_upward_imports.py $$(find $(PKG) -name '*.py')
	python scripts/check_cli_commands.py $(PKG)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +

help:
	@echo "make check     - run all verification (fmt-check + lint + test + typecheck + arch)"
	@echo "make fix       - auto-fix formatting (black) and safe ruff issues"
	@echo "make fmt       - format code in place (ruff --fix then black)"
	@echo "make fmt-check - check formatting without modifying (ruff + black --check)"
	@echo "make lint      - run custom arch-coherence/PYTHON.md §1 check"
	@echo "make test      - pytest"
	@echo "make typecheck - mypy"
	@echo "make arch      - full arch audit: lint-imports + §1 upward imports + §3 CLI tree. Scope: PKG=$(PKG) (override: make arch PKG=<path>)"
	@echo "make clean     - remove cache dirs"
