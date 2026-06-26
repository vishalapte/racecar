#!/usr/bin/env python3
"""migrate_shape.py — move a racecar `src`-shape project to `pypkg/src` (pypkg shape).

A `git mv` is the easy 1%. The other 99% is repairing every path reference the
move invalidates, because the package now sits one directory deeper. Three
reference classes, each with a deterministic rewrite (all learned the hard way on
gfem; see GENERATION.md):

  1. Markdown doc links            -> recompute with os.path.relpath to the
                                      resource's actual new location.
  2. pyproject path settings       -> setuptools `where` ["src"]->["."]; any
                                      `[tool.pylint.MASTER].ignore-paths` /
                                      `[tool.racecar...]` pattern anchored at the
                                      old source root re-anchored under pypkg/src.
  3. `__file__.parents[N]` anchors -> +1 to any N that ESCAPES the package
                                      (N > depth-from-file-to-package-root); the
                                      package's ancestors all gained one level.

Idempotent: if the project is already `pypkg`/`pypkg+djapp`, it is a no-op.
Dry-run by default; pass --apply to perform the move + rewrites, then it gates on
check_packaging + lint-imports and refuses to leave a broken tree.

Owner-authorized: this mutates working code and relocates the build root; it is
the gated step `racecar-deploy` (the web-face skill) owns. Not run on inferred
consent.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

LINK_RE = re.compile(r"\]\(([^)]+)\)")
# Path(__file__)... .parents[N]   and   Path(<pkg>.__file__)... .parents[N]
ANCHOR_RE = re.compile(
    r"(?P<base>(?:(?P<pkg>[A-Za-z_][\w.]*)\.)?__file__)(?P<mid>[^\n]*?)\.parents\[(?P<n>\d+)\]"
)

LEVELS_MOVED = 1  # src/ -> pypkg/src/ deepens the package by one directory


# --------------------------------------------------------------------------
# shape detection (mirrors PACKAGING.md "how the shape is determined")
# --------------------------------------------------------------------------


def detect_shape(repo: Path) -> str:
    """Return the repo's current packaging shape: 'pypkg', 'src', or 'unknown'."""
    pypkg = (repo / "pypkg/src/pyproject.toml").exists()
    djapp = (repo / "djapp/manage.py").exists()
    root_pj = (repo / "pyproject.toml").exists()
    django = djapp or (repo / "manage.py").exists()
    if pypkg and djapp:
        return "pypkg+djapp"
    if pypkg:
        return "pypkg"
    if root_pj and django:
        return "djapp"
    if root_pj:
        return "src"
    return "unknown"


def package_name(src_dir: Path) -> str:
    """The importable package: the lone dir under src/ holding __init__.py."""
    pkgs = [p.name for p in src_dir.iterdir() if (p / "__init__.py").exists()]
    if len(pkgs) != 1:
        raise SystemExit(f"expected exactly one package under {src_dir}, found {pkgs}")
    return pkgs[0]


# --------------------------------------------------------------------------
# class 1 — markdown doc links (relpath)
# --------------------------------------------------------------------------


def _intended_abs(repo: Path, tail: str) -> Path:
    """Map a root-relative-ish link tail to its actual location after the move."""
    if tail.startswith("src/"):
        tail = "pypkg/" + tail  # src/<pkg> -> pypkg/src/<pkg>
    elif tail == "pyproject.toml":
        tail = "pypkg/src/pyproject.toml"  # library pyproject moved with the package
    return (repo / tail).resolve()


def _strip_dots(p: str) -> str:
    parts = p.split("/")
    while parts and parts[0] in ("..", "."):
        parts.pop(0)
    return "/".join(parts)


def rewrite_links_in(path: Path, repo: Path) -> list:
    """Repair relative markdown links in one file after the src -> pypkg/src move."""
    text = path.read_text()
    fdir = path.parent
    fixes = []

    def repl(m):
        raw = m.group(1)
        if raw.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        target = raw.split("#", 1)[0]
        frag = raw[len(target) :]
        if not target or (fdir / target).resolve().exists():
            return m.group(0)
        tail = _strip_dots(target)
        if not tail:
            return m.group(0)
        absdst = _intended_abs(repo, tail)
        if not absdst.exists():
            return m.group(0)
        new = os.path.relpath(absdst, fdir) + frag
        fixes.append((raw, new))
        return f"]({new})"

    new_text = LINK_RE.sub(repl, text)
    return [(path, new_text, fixes)] if fixes else []


# --------------------------------------------------------------------------
# class 3 — __file__.parents[N] anchors (depth rule)
# --------------------------------------------------------------------------


def rewrite_anchors_in(path: Path, pkg_root: Path) -> list:
    """+1 to any parents[N] that escapes the package (reaches an ancestor)."""
    try:
        rel = path.relative_to(pkg_root)
    except ValueError:
        return []
    file_depth = (
        len(rel.parts) - 1
    )  # parents[file_depth] == pkg_root for Path(__file__)
    text = path.read_text()
    fixes = []

    def repl(m):
        n = int(m.group("n"))
        # `<pkg>.__file__` is anchored at the package root itself (depth 0),
        # `__file__` is anchored at this file (depth file_depth).
        depth = 0 if m.group("pkg") else file_depth
        if n <= depth:
            return m.group(0)  # stays inside the package; unchanged
        new_n = n + LEVELS_MOVED
        fixes.append((f"parents[{n}]", f"parents[{new_n}]"))
        return m.group(0).replace(f"parents[{n}]", f"parents[{new_n}]")

    new_text = ANCHOR_RE.sub(repl, text)
    return [(path, new_text, fixes)] if fixes else []


# --------------------------------------------------------------------------
# class 2 — pyproject path settings
# --------------------------------------------------------------------------


def rewrite_pyproject(text: str) -> tuple[str, list]:
    """Rewrite library pyproject paths (where, ignore-paths) for the pypkg shape."""
    fixes = []
    new = text
    if 'where = ["src"]' in new:
        new = new.replace('where = ["src"]', 'where = ["."]')
        fixes.append(('where = ["src"]', 'where = ["."]'))
    # re-anchor ignore-paths / pattern strings that referenced the old source root
    for m in re.findall(r'"\^src/[^"]*"', new):
        repl = m.replace("^src/", "^pypkg/src/")
        new = new.replace(m, repl)
        fixes.append((m, repl))
    return new, fixes


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------


def md_and_py(base: Path):
    """Yield every .md and .py file under base, skipping dot/venv dirs."""
    for dirpath, _, names in os.walk(base):
        if "/.venv/" in dirpath or "/__pycache__/" in dirpath:
            continue
        for n in names:
            if n.endswith((".md", ".py")):
                yield Path(dirpath) / n


def run(cmd: list, repo: Path):
    """Echo and run a git command in repo, raising on a non-zero exit."""
    print("  $", " ".join(cmd))
    subprocess.run(cmd, cwd=repo, check=True)


def main() -> None:
    """CLI entry: detect shape, then dry-run (default) or --apply the migration."""
    ap = argparse.ArgumentParser(
        description="Migrate a src-shape project to pypkg/src."
    )
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument(
        "--apply",
        action="store_true",
        help="perform the move + rewrites (default: dry-run)",
    )
    args = ap.parse_args()
    repo = args.repo.resolve()

    shape = detect_shape(repo)
    if shape != "src":
        print(f"migrate_shape: shape is already '{shape}', nothing to do (idempotent).")
        return
    pkg = package_name(repo / "src")
    print(
        f"migrate_shape: src shape, package '{pkg}'. {'APPLY' if args.apply else 'DRY-RUN'}."
    )

    if args.apply:
        run(["mkdir", "-p", "pypkg"], repo)
        run(["git", "mv", "src", "pypkg/src"], repo)
        run(["git", "mv", "pyproject.toml", "pypkg/src/pyproject.toml"], repo)

    src_base = (repo / "pypkg/src") if args.apply else (repo / "src")
    pkg_root = src_base / pkg

    # class 2: pyproject
    pj = (
        (repo / "pypkg/src/pyproject.toml") if args.apply else (repo / "pyproject.toml")
    )
    pj_new, pj_fixes = rewrite_pyproject(pj.read_text())
    print(
        f"pyproject: {len(pj_fixes)} setting(s) {'rewritten' if args.apply else 'to rewrite'}"
    )
    if args.apply and pj_fixes:
        pj.write_text(pj_new)

    # classes 1 + 3, across the moved tree (and repo-root docs)
    link_edits, anchor_edits = [], []
    targets = list(md_and_py(src_base))
    targets += [repo / "CLAUDE.md", repo / "README.md"]
    targets += list(md_and_py(repo / "docs")) if (repo / "docs").exists() else []
    for f in targets:
        if not f.exists():
            continue
        if f.suffix == ".md":
            link_edits += rewrite_links_in(f, repo)
        if f.suffix == ".py":
            anchor_edits += rewrite_anchors_in(f, pkg_root)

    n_links = sum(len(e[2]) for e in link_edits)
    n_anchors = sum(len(e[2]) for e in anchor_edits)
    print(f"doc links: {n_links} across {len(link_edits)} file(s)")
    print(f"file anchors: {n_anchors} across {len(anchor_edits)} file(s)")
    if args.apply:
        for path, new_text, _ in link_edits + anchor_edits:
            path.write_text(new_text)
        run([sys.executable, "-m", "pip", "install", "-e", "pypkg/src", "-q"], repo)
        print(
            "migrate_shape: applied. Gate with check_packaging + lint-imports before committing."
        )
    else:
        print("\nDry-run only. Re-run with --apply to perform the migration.")


if __name__ == "__main__":
    main()
