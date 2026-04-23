# Python Standards

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first

Python-specific standards. For language-agnostic architectural axioms, see [SYSTEM.md](SYSTEM.md). For Django specifics, see [DJANGO.md](DJANGO.md).

Sections are ordered as a DAG — most independent first, most dependent last.

## 1. Development Strategy

Mindset and process. No code dependencies — this is how you work, not what you write.

- **Incremental execution.** Start with a minimal, working setup before adding complexity. Prove the concept first.
- **Fail fast.** Use explicit exception handling. Avoid silent failures or broad catch-all blocks.

## 2. Naming

What things are called. Independent of structure and tooling.

- **Names describe function, not format.** A module that parses or writes data is named `data.py`, not `yaml.py` — file format is auto-detected from extension, not assumed.
- **Names are precise.** Avoid generic labels like `utils` or `helpers` when a more specific name applies.
- **Non-private functions do not start with `_`.** The underscore prefix is reserved for genuinely private methods (class name-mangling, module internals not used outside the file). If a function is called from another module, it is not private.
- **Type hints.** Use comprehensive Python type hints. Prefer `pathlib.Path` over `os.path`.

## 3. Formatting

Tool-enforced style. Independent of architecture. Two variants; pick one per project.

**Ruff variant** (recommended for new projects):
- **Formatter is canonical.** `ruff format` is enforced (black-compatible output). No manual style overrides.
- **Import ordering.** `ruff check --select I` enforces stdlib → third-party → local.

**Classic variant:**
- **Formatter is canonical.** `black` formatting is enforced.
- **Import ordering.** `isort` groups: stdlib → third-party → local.

Both variants:
- **Strings.** Use f-strings. No `%` or `.format()`.

## 4. Testing

- **Test-first (TDD).** For new features, write a basic test first to define expected behavior.
- `pytest` or `unittest` for all tests.

## 5. Module Structure

How code is organized into files and packages. Depends on naming conventions being settled.

- Package-level entry files are for orchestration and re-exports, not business logic. Logic lives in named modules.
- `__init__.py` is for module orchestration and re-exports only. If `__init__.py` has more than a few re-export lines, move the logic to a named module and re-export.

## 6. Imports

How modules connect to each other. Depends on module structure being sound.

**Direction.** Imports flow outward or downward only. This is an architectural rule — see [SYSTEM.md §1](SYSTEM.md#1-import-direction-root-axiom) for the axiom and rationale. This section covers the file-level enforcement.

**Top-level only.** All imports live at the top of the file. No exceptions. Lazy imports — imports inside functions, methods, or conditional blocks — are never acceptable. They are a band-aid over a structural problem. If moving an import to the top of the file breaks something, that breakage is the real bug. Diagnose it: extract shared code into a third module, restructure the dependency graph, or flag it for discussion. Do not bury it inside a function and move on.

**Circular dependencies.** A lazy import is usually a symptom of a circular dependency that was papered over instead of resolved. The fix is structural. See [SYSTEM.md §2](SYSTEM.md#2-no-circular-dependencies).

## 7. Linting & Verification

Final gate. Depends on everything above being correct.

- **Full-codebase scope.** Lint the entire project. Partial-set linting is not acceptable.
- **Linter returns clean output.**
  - Ruff variant: `ruff check` returns clean.
  - Classic variant: `pylint` returns clean.
- **No inline suppressions.** Neither `# noqa` (ruff/flake8), `# ruff: noqa`, `# pylint: disable=` (classic), nor `# fmt: off` / `# fmt: on` are acceptable. If the linter or formatter flags a problem, fix the code, not the suppression.

## 8. CLI

Builds on §5 Module Structure (package layout) and §6 Imports (outward-downward direction). The CLI pattern is the top layer of the dependency graph — entry points import downward, never from peers or ancestors.

Recursive outward-only discovery. Every package that contains runnable commands must provide a `__main__.py` that (a) exposes a `commands()` function and (b) prints that list when invoked with no arguments.

### Core Principles

**Packages are the preferred CLI entries; runnable modules are also valid.** A package CLI entry is a directory with a `__main__.py`. A `.py` module with an `if __name__ == "__main__":` block is also a valid entry (`python -m fubar.foo.alpha.data`). Prefer a package once the CLI grows past one file or needs its own sub-commands; keep a module for simple single-file tools.

**Unidirectional relationship.** The dependency graph is parent → child only. Parents know about their children (by registering their names). Children never reference parents. This is the CLI-layer expression of the direction axiom in [SYSTEM.md §1](SYSTEM.md#1-import-direction-root-axiom).

**Knowledge isolation.** Each `__main__.py` only declares what it directly contains — names of its immediate sub-packages (depth + 1). It does not enumerate grandchildren.

**The command contract.** Every `__main__.py` exports `commands() -> list[tuple[str, str]]` — a list of `(sub_package_name, description)` pairs. Leaves return `[]`. Names are relative; the print layer constructs full paths using `__package__`.

**Side-effect isolation.** `commands()` is a pure data function. No I/O, no network, no heavy processing. Printing the listing is confined to the `_print_commands()` helper (Patterns 1 and 2). Leaf CLIs (Pattern 3) delegate all output to `argparse`. No other CLI functions should call `print()` directly.

### Implementation Blueprint

Sample tree used throughout. Directories with `__main__.py` are CLI entry points. A `.py` module with an `if __name__ == "__main__":` guard is also a valid entry point. The `.py` files shown in this tree are utility modules — no main guard, imported by the neighboring `__main__.py`.

```
src/fubar/
  __init__.py
  __main__.py          ← CLI entry: python -m fubar   (root aggregator)
  foo/
    __init__.py
    __main__.py        ← CLI entry: python -m fubar.foo   (intermediate with own CLI)
    alpha/
      __init__.py
      __main__.py      ← CLI entry: python -m fubar.foo.alpha   (leaf CLI)
      data.py          ← utility module (imported by alpha's __main__; NOT a CLI entry)
  baz/
    __init__.py
    __main__.py        ← CLI entry: python -m fubar.baz   (intermediate, discovery only)
    alpha/
      __init__.py
      __main__.py      ← CLI entry: python -m fubar.baz.alpha
      data.py          ← utility module
    bravo/
      __init__.py
      __main__.py      ← CLI entry: python -m fubar.baz.bravo
      calculator.py    ← utility module
```

There are three patterns. Each `__main__.py` matches exactly one.

---

#### Pattern 1 — Pure discovery (root or intermediate without own CLI)

Lists sub-packages. No CLI of its own. Always prints the listing and exits.

Used by `fubar/__main__.py` (root) and `fubar/baz/__main__.py` (intermediate with no own CLI).

```python
"""CLI entry: python -m fubar"""

import sys


def commands() -> list[tuple[str, str]]:
    return [
        ("foo", "Foo sub-package: [one-line description]"),
        ("baz", "Baz sub-package: [one-line description]"),
    ]


def _print_commands() -> None:
    entries = [(f"python -m {__package__}.{n}", d) for n, d in commands()]
    width = max(len(p) for p, _ in entries)
    print(f"python -m {__package__}\n")
    for path, desc in entries:
        print(f"  {path.ljust(width)}   {desc}")
    print("\nAppend --help to any command for its options.")


if __name__ == "__main__":
    _print_commands()
    sys.exit(0)
```

---

#### Pattern 2 — Discovery plus own CLI (intermediate that both aggregates and runs)

Lists sub-packages. Has its own argparse CLI. No-args prints the listing; args runs the CLI.

Used by `fubar/foo/__main__.py`.

```python
"""CLI entry: python -m fubar.foo"""

import argparse
import sys


def commands() -> list[tuple[str, str]]:
    return [
        ("alpha", "Alpha sub-package: [one-line description]"),
    ]


def _print_commands() -> None:
    entries = [(f"python -m {__package__}.{n}", d) for n, d in commands()]
    width = max(len(p) for p, _ in entries)
    print(f"python -m {__package__}\n")
    for path, desc in entries:
        print(f"  {path.ljust(width)}   {desc}")
    print("\nAppend --help to any command for its options.")


def main() -> None:
    if not sys.argv[1:]:
        _print_commands()
        return
    parser = argparse.ArgumentParser(description="foo CLI")
    # argument definitions
    args = parser.parse_args()
    run(args)


def run(args: argparse.Namespace) -> None:
    """Project-specific dispatch goes here."""
    raise NotImplementedError("Implement dispatch for this CLI")


if __name__ == "__main__":
    main()
```

Note: `_print_commands()` is duplicated verbatim in Patterns 1 and 2. This is a deliberate self-containment choice — each `__main__.py` stands alone with no shared utility module. The function is six lines; the coupling cost of sharing it exceeds the duplication cost.

---

#### Pattern 3 — Leaf CLI (package with no sub-packages)

No sub-packages to discover. `commands()` returns `[]`. The `__main__.py` IS the CLI — argparse handles everything including `--help`.

Used by `fubar/foo/alpha/__main__.py`, `fubar/baz/alpha/__main__.py`, `fubar/baz/bravo/__main__.py`.

```python
"""CLI entry: python -m fubar.foo.alpha"""

import argparse


def commands() -> list[tuple[str, str]]:
    return []  # leaf — no sub-packages


def main() -> None:
    parser = argparse.ArgumentParser(description="alpha CLI")
    # argument definitions
    args = parser.parse_args()
    run(args)


def run(args: argparse.Namespace) -> None:
    """Project-specific dispatch goes here."""
    raise NotImplementedError("Implement dispatch for this CLI")


if __name__ == "__main__":
    main()
```

---

### Expected CLI Behaviour

```
python -m fubar
  python -m fubar.foo   Foo sub-package: [one-line description]
  python -m fubar.baz   Baz sub-package: [one-line description]

python -m fubar.foo
  python -m fubar.foo.alpha   Alpha sub-package: [one-line description]

python -m fubar.baz
  python -m fubar.baz.alpha   Alpha sub-package: [one-line description]
  python -m fubar.baz.bravo   Bravo sub-package: [one-line description]

python -m fubar.foo.alpha           # runs alpha's argparse CLI (shows help if needed)
python -m fubar.foo --flag value    # runs foo's own CLI
python -m fubar.foo.alpha.data      # runs data.py if it has `if __name__ == "__main__":`; no-op if not
```

### Rules

| Rule | Rationale |
|------|-----------|
| Packages are the preferred CLI entry; runnable `.py` modules with `if __name__ == "__main__":` are also valid | Packages scale to sub-commands; modules stay simple for single-file tools |
| No inward references in `__main__.py` — no `from ..` | Prevents upward references that would couple children to parents (see [SYSTEM.md §1](SYSTEM.md#1-import-direction-root-axiom)) and mask circular deps (see [SYSTEM.md §2](SYSTEM.md#2-no-circular-dependencies)) |
| `commands()` returns relative names, not full paths | `__package__` constructs the path; names stay readable |
| `commands()` lists immediate children — sub-packages or runnable modules | Either is a valid invocation target via `python -m {parent}.{child}` |
| Parents register child names explicitly — no dynamic discovery | Explicit registration; no invisible capabilities |
| Depth + 1 only — never enumerate grandchildren | Each layer owns its own listing |
| Leaves return `commands() == []` | Keeps the contract uniform across all `__main__.py` files |
| Packages with their own CLI run it when args are given | No-args = listing; args = action |
| Printing confined to `_print_commands()` (Patterns 1 & 2) or `argparse` (Pattern 3) | Side-effect isolation; keeps listing logic testable without capturing stdout from arbitrary call sites |

### Registration

New sub-packages must be manually added to the parent's `commands()` list. This is intentional. Dynamic discovery hides what the system can do. Explicit registration makes capabilities visible and auditable.

When a new `__main__.py` is added, update the parent's `commands()` before merging.

## 9. Definition of Done

After modifying code, verify:

1. **Format + safe fixes.**
   - Ruff variant: `ruff check --fix src/` then `black src/`.
   - Classic variant: `isort src/` then `black src/`.
2. **Lint clean.**
   - Ruff variant: `ruff check src/` passes.
   - Classic variant: `pylint src/` passes.
3. Test suite passes with 0 regressions.
4. No `print()` statements in business logic. `print()` is permitted only in CLI entry files (`__main__.py`) via `_print_commands()` (Patterns 1 & 2) or `argparse` output (Pattern 3) — see §8. No temporary `TODO`s remain.

## 10. Enforcement

SYSTEM.md rules are enforced mechanically via `import-linter` (DAG/cycle checks) and `pre-commit` (orchestration). The per-project contract lives in `pyproject.toml`; the orchestrator config in `.pre-commit-config.yaml`.

Templates live in [`../templates/`](templates/). To adopt on a new project:

1. Pick a variant under `../templates/`:
   - `ruff/` (recommended for new projects — ruff for lint, black for format)
   - `classic/` (black + isort + pylint)
2. Copy all blocks from the chosen variant's `pyproject.toml` into your project's `pyproject.toml` (merge into an existing file if present). Skip blocks that don't apply (e.g. `[tool.mypy]` if you don't type-check).
3. Copy the chosen variant's `pre-commit-config.yaml` to your project root as `.pre-commit-config.yaml` (add the leading dot on copy).
4. Copy the chosen variant's `Makefile` to your project root.
5. Copy `../templates/scripts/` to your project's `scripts/` directory (shared across both variants).
6. Replace `<root>` with your top-level package name, and fill the layer rows with your own packages.
7. Install and enable:
   - Ruff variant: `pip install pre-commit ruff black mypy import-linter pytest && pre-commit install`
   - Classic variant: `pip install pre-commit black isort pylint mypy import-linter pytest && pre-commit install`

### Update triggers — when to modify pyproject.toml

Any architectural change in the source tree requires a matching edit to `[tool.importlinter]` in the same commit:

1. New top-level package → add it to the layer matching its role (consumer / data / leaf).
2. Top-level package removed → remove its entry.
3. New peer direction (A now imports B where they were independent) → split A and B into separate layer rows (B below A), or add a `forbidden` contract:

   [[tool.importlinter.contracts]]
   name = "B does not import A"
   type = "forbidden"
   source_modules = ["<root>.<B>"]
   forbidden_modules = ["<root>.<A>"]

4. Peer direction reversed or removed → update layers or the forbidden contract.
5. Package changes role (leaf → consumer, etc.) → move to the appropriate layer row.

### Instruction to Claude or any agent

When making any architectural change under the source tree — adding a package, moving a module between packages, establishing a new peer import — update `[tool.importlinter]` in `pyproject.toml` in the same commit. The contract is source-of-truth for the dependency graph. If contract and code disagree, `lint-imports` fails and pre-commit rejects the commit.

### Verification

After editing the contract, run `lint-imports`. Output should be `Contracts: N kept, 0 broken.` If broken: either the code doesn't match the claimed architecture (fix the code) or the contract is stale (fix the contract).

### Template updates

`../templates/` is the canonical source. When the templates evolve (new pinned versions, new custom checks), consumer projects pull changes in by manually re-copying. `diff -u ../templates/<variant>/pre-commit-config.yaml .pre-commit-config.yaml` (where `<variant>` is `ruff` or `classic`) shows drift; merge intentionally.
