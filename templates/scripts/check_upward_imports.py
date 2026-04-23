#!/usr/bin/env python3
"""Enforce SYSTEM.md §4: business modules must not import directly from the root package.

Only `__init__.py` files may import from the root package (the environment-layer
channel). Business modules that need inherited state read it via their own
package's `__init__.py`. This script rejects any line matching
`from <root> import ...` in files that are neither `__init__.py` nor `__main__.py`.

The root package name is read from `pyproject.toml`'s `[tool.importlinter].root_package`.

Usage (invoked by pre-commit):
    python scripts/check_upward_imports.py <file> [<file> ...]

Exits 0 if clean, 1 if any violation is found.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


def _root_package() -> str:
    pyproject = Path("pyproject.toml")
    if not pyproject.is_file():
        print("check_upward_imports: pyproject.toml not found", file=sys.stderr)
        sys.exit(2)
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    try:
        return data["tool"]["importlinter"]["root_package"]
    except KeyError:
        print(
            "check_upward_imports: [tool.importlinter].root_package missing from pyproject.toml",
            file=sys.stderr,
        )
        sys.exit(2)


def _check(path: Path, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if pattern.match(line):
            violations.append((lineno, line.rstrip()))
    return violations


def main(argv: list[str]) -> int:
    root = _root_package()
    pattern = re.compile(rf"^\s*from\s+{re.escape(root)}\s+import\s+")
    skip_suffixes = ("__main__.py", "__init__.py")
    total = 0
    for arg in argv:
        path = Path(arg)
        if path.name in skip_suffixes or not path.is_file():
            continue
        for lineno, line in _check(path, pattern):
            print(f"{path}:{lineno}: upward import forbidden: {line}")
            total += 1
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
