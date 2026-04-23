# templates/ruff/Makefile — copy to project root (no rename needed).
# `make check` is the canonical verification entry point.

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
	@echo "make lint      - run custom SYSTEM.md §4 check"
	@echo "make test      - pytest"
	@echo "make typecheck - mypy"
	@echo "make arch      - lint-imports (DAG check)"
	@echo "make clean     - remove cache dirs"
