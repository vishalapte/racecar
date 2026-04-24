#!/usr/bin/env python3
"""Enforce arch-coherence/PYTHON.md §3: the `__main__.py` + `commands()` CLI contract.

Scope is deliberately narrow: this script checks commands only. It does not
reimplement §1 (Module Structure) or §2 (Imports) — those are owned by
`import-linter` (acyclicity, direction) and `check_upward_imports.py` (upward
imports from business modules). Run those alongside this one.

At every node in the CLI tree rooted at `<pkg>` the walker confirms:

1. The package exposes `commands() -> list[tuple[str, str]]` with direct-child
   names (no dots).
2. Symbol presence matches one of the three patterns:
     - `commands()` non-empty + no `main()`    → Pattern 1 (pure discovery)
     - `commands()` non-empty +  `main()`      → Pattern 2 (discovery + own CLI)
     - `commands()` empty     +  `main()`      → Pattern 3 (leaf)
   Patterns 1 and 2 must also expose `_print_commands()` — every intermediate
   owns its own print layer, no inheritance.
3. Subprocess behaviour matches the pattern:
     - `python -m <pkg>` with no args exits 0 at every node.
     - For non-empty `commands()`, the no-args output lists exactly one
       `python -m <pkg>.<name>   <desc>` line per entry and stdout is non-empty.
     - `python -m <pkg> --help` exits 0 at every node.
4. Each listed child `<pkg>.<name>` is a real, runnable entry point — either a
   sub-package with its own `__main__.py` (recurse into it) or a `.py` module
   with an `if __name__ == "__main__":` guard.
5. Registration symmetry: the filesystem under `pkg` is scanned for any
   direct-child sub-package with a `__main__.py`, or any `.py` module with an
   `if __name__ == "__main__":` guard, that is NOT in `commands()`. These are
   orphan CLIs — hidden capabilities that no parent names. §3 is explicit:
   registration is manual, not dynamic, so an unregistered deeper `__main__.py`
   is a violation. Orphan sub-packages are descended into so their own subtrees
   are audited too.

# Importable API

    from scripts.check_cli_commands import audit_cli_tree
    tree = audit_cli_tree("fubar")        # nested dict, JSON-serialisable

Each node in the returned tree has this schema:

    {
      "pkg":        str,                    # dotted package name
      "kind":       "package" | "module" | "missing",
      "pattern":    "pattern-1" | "pattern-2" | "pattern-3" | "unknown",
      "commands":   [[str, str], ...] | null,
      "orphan":     bool,                   # was this node registered by its parent
      "violations": [str, ...],             # messages at this node only
      "children":   [<node>, ...],          # registered children + orphans, in order
    }

# CLI

    python scripts/check_cli_commands.py <root.package> [<root.package> ...]
    python scripts/check_cli_commands.py --json <root.package>

Default output is the walked tree plus a violations summary. With `--json`,
emits the audit dict (single root) or a list of dicts (multiple roots) to stdout.

Exits 0 if clean, 1 if any violation is found.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

_LINE_RE = re.compile(r"^\s+python -m (?P<path>\S+)\s{2,}(?P<desc>.+?)\s*$")

_PATTERN_LABEL = {
    "pattern-1": "Pattern 1 (pure discovery)",
    "pattern-2": "Pattern 2 (discovery + own CLI)",
    "pattern-3": "Pattern 3 (leaf)",
    "unknown": "?",
}

Node = dict[str, Any]


# ---------- discovery helpers -------------------------------------------- #


def _import_main(pkg: str) -> ModuleType | None:
    try:
        return importlib.import_module(f"{pkg}.__main__")
    except ModuleNotFoundError:
        return None


def _read_commands(mod: ModuleType) -> tuple[list[tuple[str, str]] | None, list[str]]:
    fn = getattr(mod, "commands", None)
    if fn is None:
        return None, ["missing `commands()` function in __main__.py"]
    try:
        result = fn()
    except Exception as exc:
        return None, [f"`commands()` raised {type(exc).__name__}: {exc}"]
    if not isinstance(result, list) or not all(
        isinstance(p, tuple) and len(p) == 2 and all(isinstance(s, str) for s in p) for p in result
    ):
        return None, [f"`commands()` must return list[tuple[str, str]]; got {result!r}"]
    bad_names = [n for n, _ in result if "." in n or not n]
    if bad_names:
        return result, [f"`commands()` entries must be direct child names, not dotted: {bad_names}"]
    return result, []


def _run(pkg: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", pkg, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_listing(stdout: str) -> list[tuple[str, str]]:
    return [(m["path"], m["desc"]) for line in stdout.splitlines() if (m := _LINE_RE.match(line))]


def _classify(mod: ModuleType, commands: list[tuple[str, str]]) -> tuple[str, list[str]]:
    has_main = callable(getattr(mod, "main", None))
    has_print = callable(getattr(mod, "_print_commands", None))
    violations: list[str] = []
    if commands:
        pattern = "pattern-2" if has_main else "pattern-1"
        if not has_print:
            violations.append(
                f"{_PATTERN_LABEL[pattern]}: missing `_print_commands()` (every intermediate node owns its print layer)"
            )
    else:
        pattern = "pattern-3"
        if not has_main:
            violations.append("Pattern 3 (leaf): missing `main()` — argparse entry point required")
    return pattern, violations


def _has_main_guard(source: str) -> bool:
    return 'if __name__ == "__main__"' in source or "if __name__ == '__main__'" in source


def _list_direct_subpackages(pkg: str) -> list[str]:
    """All direct-child sub-packages (dirs with __init__.py), regardless of
    whether they have __main__.py. Alphabetical."""
    try:
        mod = importlib.import_module(pkg)
    except ModuleNotFoundError:
        return []
    paths = getattr(mod, "__path__", None)
    if not paths:
        return []
    names: list[str] = []
    seen_names: set[str] = set()
    for base in paths:
        base_path = Path(base)
        if not base_path.is_dir():
            continue
        for entry in sorted(base_path.iterdir()):
            if entry.name.startswith((".", "_")):
                continue
            if entry.is_dir() and (entry / "__init__.py").is_file() and entry.name not in seen_names:
                seen_names.add(entry.name)
                names.append(entry.name)
    return names


def _scan_disk_children(pkg: str) -> tuple[list[str], list[str]]:
    """Return (sub_packages_with_main_py, modules_with_main_guard) as direct-child names."""
    try:
        mod = importlib.import_module(pkg)
    except ModuleNotFoundError:
        return [], []
    paths = getattr(mod, "__path__", None)
    if not paths:
        return [], []
    sub_packages: list[str] = []
    modules: list[str] = []
    seen_names: set[str] = set()
    for base in paths:
        base_path = Path(base)
        if not base_path.is_dir():
            continue
        for entry in sorted(base_path.iterdir()):
            if entry.name.startswith((".", "_")):
                continue
            if entry.is_dir() and (entry / "__init__.py").is_file():
                name = entry.name
                if name in seen_names:
                    continue
                seen_names.add(name)
                if (entry / "__main__.py").is_file():
                    sub_packages.append(name)
            elif entry.is_file() and entry.suffix == ".py" and entry.name != "__main__.py":
                name = entry.stem
                if name in seen_names:
                    continue
                try:
                    source = entry.read_text(encoding="utf-8")
                except OSError:
                    continue
                if _has_main_guard(source):
                    seen_names.add(name)
                    modules.append(name)
    return sub_packages, modules


def _make_node(pkg: str, *, orphan: bool) -> Node:
    return {
        "pkg": pkg,
        "kind": "missing",
        "pattern": "unknown",
        "commands": None,
        "orphan": orphan,
        "violations": [],
        "children": [],
    }


def _descend_broken(node: Node, pkg: str, seen: set[str]) -> None:
    """Recover traversal when a node is broken (no __main__.py or no valid
    commands()). Every direct-child sub-package on disk is audited so hidden
    CLI entries further down still become visible."""
    for name in _list_direct_subpackages(pkg):
        child_pkg = f"{pkg}.{name}"
        node["children"].append(_audit_package(child_pkg, orphan=False, seen=seen))
    _, disk_modules = _scan_disk_children(pkg)
    for name in disk_modules:
        child_pkg = f"{pkg}.{name}"
        orphan_node = _make_node(child_pkg, orphan=True)
        orphan_node["kind"] = "module"
        orphan_node["pattern"] = "pattern-3"
        node["violations"].append(
            f'§3 orphan runnable module: `{child_pkg}` has main guard but '
            f"parent `{pkg}` cannot register it (no valid commands())"
        )
        node["children"].append(orphan_node)


def _audit_package(pkg: str, *, orphan: bool, seen: set[str]) -> Node:
    """Audit one package node and recurse into its children. Returns a Node dict."""
    node = _make_node(pkg, orphan=orphan)

    if pkg in seen:
        node["violations"].append("already visited — cycle in CLI tree")
        return node
    seen.add(pkg)

    mod = _import_main(pkg)
    if mod is None:
        node["violations"].append("no __main__.py (not importable as `python -m ...`)")
        _descend_broken(node, pkg, seen)
        return node
    node["kind"] = "package"

    commands, cmd_violations = _read_commands(mod)
    node["violations"].extend(cmd_violations)
    if commands is None:
        _descend_broken(node, pkg, seen)
        return node
    node["commands"] = [[name, desc] for name, desc in commands]

    pattern, classify_violations = _classify(mod, commands)
    node["pattern"] = pattern
    node["violations"].extend(classify_violations)

    # Uniform: --help exits 0 everywhere.
    help_result = _run(pkg, "--help")
    if help_result.returncode != 0:
        node["violations"].append(
            f"`python -m {pkg} --help` exited {help_result.returncode}; stderr: {help_result.stderr.strip()[:200]}"
        )

    if commands:
        noargs = _run(pkg)
        if noargs.returncode != 0:
            node["violations"].append(
                f"`python -m {pkg}` (no args) exited {noargs.returncode}; stderr: {noargs.stderr.strip()[:200]}"
            )
        elif not noargs.stdout.strip():
            node["violations"].append(f"`python -m {pkg}` (no args) exited 0 but produced no stdout")
            if noargs.stderr.strip():
                node["violations"].append("  (stderr was non-empty — listing may be going to the wrong stream)")
        else:
            printed = _parse_listing(noargs.stdout)
            expected = [(f"{pkg}.{name}", desc) for name, desc in commands]
            printed_set = {p for p, _ in printed}
            expected_set = {p for p, _ in expected}
            for path, _desc in expected:
                if path not in printed_set:
                    node["violations"].append(
                        f"`commands()` claims `{path}` but no-args output does not list it"
                    )
            for path, _desc in printed:
                if path not in expected_set:
                    node["violations"].append(
                        f"no-args output lists `{path}` but `commands()` does not claim it"
                    )
            printed_desc = dict(printed)
            for path, desc in expected:
                if path in printed_desc and printed_desc[path] != desc:
                    node["violations"].append(
                        f"description mismatch for `{path}`: commands()={desc!r}, printed={printed_desc[path]!r}"
                    )

    # Registered children.
    registered = set()
    for name, _desc in commands:
        registered.add(name)
        child_pkg = f"{pkg}.{name}"
        if _import_main(child_pkg) is not None:
            node["children"].append(_audit_package(child_pkg, orphan=False, seen=seen))
            continue
        # No __main__.py. Is the child a package (missing __main__.py) or a
        # runnable .py module?
        try:
            child_mod = importlib.import_module(child_pkg)
        except ModuleNotFoundError:
            child_node = _make_node(child_pkg, orphan=False)
            child_node["violations"].append(
                f"`commands()` lists `{name}` but `{child_pkg}` is not importable"
            )
            node["children"].append(child_node)
            continue
        if hasattr(child_mod, "__path__"):
            # Package without __main__.py; _audit_package handles that case.
            node["children"].append(_audit_package(child_pkg, orphan=False, seen=seen))
            continue
        # .py module candidate — check for main guard.
        child_node = _make_node(child_pkg, orphan=False)
        source_file = getattr(child_mod, "__file__", None)
        if not source_file:
            child_node["violations"].append(
                f"`{child_pkg}` has no source file; cannot verify main guard"
            )
            node["children"].append(child_node)
            continue
        try:
            source = Path(source_file).read_text(encoding="utf-8")
        except OSError as exc:
            child_node["violations"].append(f"cannot read `{child_pkg}` source ({source_file}): {exc}")
            node["children"].append(child_node)
            continue
        if not _has_main_guard(source):
            child_node["kind"] = "module"
            child_node["pattern"] = "pattern-3"
            child_node["violations"].append(
                f'`commands()` lists `{name}` but `{child_pkg}` has no `if __name__ == "__main__":` guard'
            )
            node["children"].append(child_node)
            continue
        child_node["kind"] = "module"
        child_node["pattern"] = "pattern-3"
        node["children"].append(child_node)

    # Orphan scan — direct-child CLI entries on disk not in commands().
    disk_subpkgs, disk_modules = _scan_disk_children(pkg)
    for name in disk_subpkgs:
        if name in registered:
            continue
        child_pkg = f"{pkg}.{name}"
        node["violations"].append(
            f"§3 orphan sub-package CLI: `{child_pkg}` has __main__.py but is not in parent's commands()"
        )
        node["children"].append(_audit_package(child_pkg, orphan=True, seen=seen))
    for name in disk_modules:
        if name in registered:
            continue
        child_pkg = f"{pkg}.{name}"
        orphan_node = _make_node(child_pkg, orphan=True)
        orphan_node["kind"] = "module"
        orphan_node["pattern"] = "pattern-3"
        node["violations"].append(
            f'§3 orphan runnable module: `{child_pkg}` has `if __name__ == "__main__":` '
            f"but is not in parent's commands()"
        )
        node["children"].append(orphan_node)

    return node


# ---------- public API --------------------------------------------------- #


def audit_cli_tree(root: str) -> Node:
    """Walk the CLI tree rooted at `root` and return the audit as a nested dict.

    The returned Node is JSON-serialisable. See module docstring for schema.
    """
    return _audit_package(root, orphan=False, seen=set())


def collect_violations(node: Node) -> list[tuple[str, str]]:
    """Flatten a tree into a list of (pkg, message) pairs in pre-order."""
    out: list[tuple[str, str]] = [(node["pkg"], msg) for msg in node["violations"]]
    for child in node["children"]:
        out.extend(collect_violations(child))
    return out


# ---------- rendering ---------------------------------------------------- #


def _node_status(node: Node) -> str:
    if node["violations"]:
        return f"FAIL ({len(node['violations'])})"
    return "OK"


def render_tree(node: Node, depth: int = 0) -> list[str]:
    """Render a tree as indented human-readable lines (list, so caller joins)."""
    indent = "  " * depth
    pattern_label = _PATTERN_LABEL.get(node["pattern"], node["pattern"])
    kind_suffix = ""
    if node["kind"] == "module":
        kind_suffix = " runnable module"
    if node["orphan"]:
        kind_suffix += " (orphan)"
    line = f"{indent}python -m {node['pkg']}   [{pattern_label}{kind_suffix}] {_node_status(node)}"
    lines = [line]
    for child in node["children"]:
        lines.extend(render_tree(child, depth + 1))
    return lines


# ---------- CLI ---------------------------------------------------------- #


def _resolve_root(arg: str) -> str:
    """Turn `src/gfem` or `./src/gfem` into `gfem`, with the enclosing directory
    added to sys.path so the package becomes importable. Dotted names pass
    through unchanged."""
    path = Path(arg)
    looks_like_path = ("/" in arg) or ("\\" in arg) or path.exists()
    if not looks_like_path:
        return arg
    abs_path = path.resolve()
    if not abs_path.is_dir():
        raise SystemExit(f"check_cli_commands: `{arg}` is not a directory")
    if not (abs_path / "__init__.py").is_file():
        raise SystemExit(
            f"check_cli_commands: `{arg}` has no __init__.py; not a Python package"
        )
    parent = str(abs_path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return abs_path.name


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Audit the CLI tree rooted at one or more Python packages.",
    )
    parser.add_argument(
        "roots",
        nargs="+",
        help="Dotted package names (e.g. `gfem`) or filesystem paths to the package directory (e.g. `src/gfem`).",
    )
    parser.add_argument("--json", action="store_true", help="Emit the audit tree as JSON.")
    args = parser.parse_args(argv)

    roots = [_resolve_root(r) for r in args.roots]
    trees = [audit_cli_tree(root) for root in roots]
    all_violations: list[tuple[str, str]] = []
    for tree in trees:
        all_violations.extend(collect_violations(tree))

    if args.json:
        payload = trees[0] if len(trees) == 1 else trees
        print(json.dumps(payload, indent=2))
    else:
        for root, tree in zip(roots, trees):
            print(f"\n=== {root} ===")
            for line in render_tree(tree):
                print(line)
        if all_violations:
            print("\n--- violations ---")
            for pkg, msg in all_violations:
                print(f"{pkg}: {msg}")
        else:
            print("\nAll checks passed.")

    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
