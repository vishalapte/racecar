# Root Makefile — self-verification for this framework's own docs.
# `make check-docs` runs the mechanical pre-pass defined in doc-coherence/README.md.

# Auto-detect venv (order: .venv, venv, ../venv). If found, prepend its
# bin/ to PATH so tooling resolves to the venv rather than system binaries.
VENV := $(firstword $(wildcard .venv venv ../venv))
ifdef VENV
  export PATH := $(abspath $(VENV))/bin:$(PATH)
endif
PYTHON := $(if $(VENV),$(VENV)/bin/python3,python3)

.PHONY: check-docs help

check-docs:
	$(PYTHON) doc-coherence/scripts/check_docs.py

help:
	@echo "make check-docs - run the mechanical pre-pass on this repo's own docs"
