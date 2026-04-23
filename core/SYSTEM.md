# System Standards

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first

Language-agnostic architectural axioms. For the Python application of these principles in CLI design, see [PYTHON.md ## CLI](PYTHON.md#8-cli).

Sections are ordered as a DAG — most independent first, most dependent last. Everything below derives from one axiom: **the import graph is acyclic.**

## 1. No Cycles (root axiom)

The primary rule is absolute: the import graph must be acyclic. At every level — packages, modules, functions — the dependency graph is a DAG. This is non-negotiable.

When `A` imports `B` imports `A`, the cycle is an architectural bug. Resolve it by extracting the shared dependency into a third module that both can import, or by moving the function to the side that already has the import.

Lazy imports (imports inside functions) are the usual symptom — the quickest way to get a circular import to "compile" is to defer it, which hides the real bug. For the file-level rule that surfaces cycles instead of hiding them, see [PYTHON.md §6 Imports](PYTHON.md#6-imports).

The rules below describe preferred directions that make acyclicity clear at a glance. They are not stricter than the axiom — they are its practical form.

See [PYTHON.md §10 Enforcement](PYTHON.md#10-enforcement) for how this axiom is verified mechanically.

## 2. Direction in the Package Tree

```
fubar/                ← root package
  foo/                ← child of fubar
    alpha/            ← child of foo; leaf package
      data            ← leaf module
  baz/                ← child of fubar; peer of foo
    alpha/
      data
    bravo/
      calculator
```

Three kinds of import edge, three rules:

**Outward / downward (parent → child).** Always allowed. A parent package imports from its subtree. `fubar` imports from `fubar.foo`. This is the default direction.

**Peer → peer.** Allowed in **one direction only**. If `foo` imports `baz`, then `baz` must never import `foo` — directly or transitively. Multiple peers may depend on the same peer (many-to-one fan-in is fine); what is forbidden is any return edge. Once the direction is established, it is fixed.

**Upward (child → parent).** Forbidden for business logic. The environment-layer exception (§3) is the only carve-out.

## 3. Environment Layer Exception

Configuration derived from outside the project — environment variables, `.env` files, CLI flags parsed at the top — is an environment layer. It typically lives in the root package's `__init__.py` or a dedicated `config`/`core` module. Any module in the tree may import from the environment layer; this is semantically equivalent to importing external state. The outward rule applies to business-logic dependencies, not to environment access.

**Constraint on the environment layer.** The environment layer must not import from its children at module load. Read env, compute constants, done. Importing a child during the layer's initialization reintroduces the very circularity the axiom prevents — the child will try to import back to get its configuration, and the layer is not yet fully initialized.

## 4. `__main__.py` and `__init__.py`: Opposite Roles

Every package has two specialty files, and they point in opposite directions on the dependency graph.

**`__main__.py` imports outward.** It is the execution entry point. It reaches down into the package's own subtree to dispatch work. Its dependencies go inward-subtree only; never upward to a parent package (env layer excepted).

**`__init__.py` may import upward — only to the environment layer.** It is the package's face to the outside: it declares what the package IS when imported. When a child package needs inherited state, its `__init__.py` imports from the environment layer and re-exports into its own namespace. Internal modules then import from their own package's `__init__.py`, not from the root directly.

This channels the upward direction through one visible file per package. The ambient state a package depends on is locatable in one place.

**Other `.py` modules never import upward directly.** Business-logic modules stay within their own subtree, import from peers in the allowed direction (§2), or read inherited state through their own package's `__init__.py`.

See [PYTHON.md ## CLI](PYTHON.md#8-cli) for the Python-specific `__main__.py` + `commands()` pattern that enforces the outward rule structurally.

## 5. Domain Boundaries

Packages should be loosely coupled, even where peer imports are allowed. Before adding a peer edge:

- Does the graph stay acyclic? (§1 is non-negotiable.)
- Is the direction consistent with existing peer edges at that level?
- Would the shared concept fit better one layer up? If two peers would genuinely need to depend on each other mutually, extract to a common parent or a `core` module.

Peer imports work best when one peer is a pure types/utilities provider (for example, a `battery` package defining `BatteryParams`) and the others consume. Peer imports fail when both peers try to orchestrate each other.

## 6. Layered Dependency Graph

The system has a fixed layer order. Dependencies only go downward through the layers:

```
Entry points            ← top layer; imports orchestrators and domain
  Orchestrators         ← coordinates; imports domain
    Domain modules      ← business logic; imports utilities
      Pure utilities    ← math, format, I/O helpers; imports external only
```

Nothing in a lower layer imports from a layer above it. If a utility needs orchestration logic, that logic has been placed in the wrong layer.

An *orchestrator* is a module that coordinates domain modules to produce a feature-level outcome — for example, a build script that calls compute, database, and export in sequence; a request handler that composes several services; or a CLI entry point that routes to sub-commands. Orchestrators are stateful in the sense that they know which pieces to run in which order; domain modules and utilities are not.
