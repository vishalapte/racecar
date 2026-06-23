# Architectural Coherence

The lens that keeps a system's import graph honest: acyclic, flowing one direction, layers that don't leak, one library exposed through thin faces. It catches the architectural rot tests never see — import cycles, a module reaching up into its own root, a library smeared across a dozen entry points.

Run it with `/racecar-arch-coherence`, or `make arch` for the mechanical subset (`import-linter` plus the check scripts).

**When to reach for it:** reviewing architecture, chasing an import cycle, auditing dependency direction, or checking whether the architecture the docs claim matches the import graph the code actually has.

**What a finding looks like:** `fubar/utils/date.py` imports `fubar.billing.invoice` — a utility reaching up into orchestration. *Major: utilities must not depend upward; move the shared concept up a layer.*

## What's here

| Doc | Covers |
|---|---|
| [`AXIOMS.md`](AXIOMS.md) | **Start here.** The review lens: the four DAG axioms (acyclicity, direction, layer integrity, depth-plus-one), red flags, feedback format. |
| [`FACES.md`](FACES.md) | The `lib → api → faces` shape: one library, thin faces, the gated `layers` contract, the advisory orchestration detector. |
| [`PYTHON.md`](PYTHON.md) | Python specifics: module structure, `__init__.py` / `__main__.py` roles, `import-linter` enforcement. |
| [`DJANGO.md`](DJANGO.md) | Django specifics: service layer, view layering. |
| [`CLI.md`](CLI.md) | The CLI surface contract: `__main__.py`, `commands()` / `subcommands()` / `parser()`, audit JSON. |
| [`PACKAGING.md`](PACKAGING.md) | The project shell: pyproject, the `Makefile` contract, the four project shapes, dev tooling, governance. |

Pair with [`../eng-review/README.md`](../eng-review/README.md) for code-level hygiene and [`../doc-coherence/README.md`](../doc-coherence/README.md) for prose and cross-references. The human storefront is the repo [`../README.md`](../README.md).
