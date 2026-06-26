# racecar-reshape — the procedure

Accessed via [`SKILL.md`](SKILL.md). Doctrine home: [`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md)
(the shapes axis). Mechanism: [`../arch-coherence/scripts/migrate_shape.py`](../arch-coherence/scripts/migrate_shape.py).

## What this skill is for

Move a project from one racecar packaging shape to another. Today the one
supported transition is **`src` → `pypkg/src`** (the `pypkg` shape): nest the
installable package under `pypkg/` so the repo can grow a second installable
root or a Django app (`pypkg+djapp`) without the build roots fighting.

It is the shapes-axis prerequisite. It does **not** touch the faces axis (no
`api` insertion, no REST/MCP, no djapp). `racecar-deploy` stacks those on top;
`racecar-upgrade` calls this for its optional structural uplift.

## Why it is not a `git mv`

Moving the package one directory deeper invalidates every path reference that
crossed the old boundary. The `git mv` is ~1% of the work; the repairs are the
rest, and there are exactly three classes — each deterministic:

1. **Markdown doc links.** Recomputed with `os.path.relpath` against the
   resource's actual new location. Links to root-only resources (`docs/`,
   `Makefile`, `CHANGELOG.md`) gain one `../`; the link to the library
   `pyproject.toml` loses one (it moved *with* the package); links naming the
   old `src/<pkg>` path become `pypkg/src/<pkg>`.
2. **pyproject path settings.** setuptools `[tool.setuptools.packages.find].where`
   `["src"]` → `["."]`; any pattern anchored at the old source root
   (`[tool.pylint.MASTER].ignore-paths` `^src/...`, which also gates the
   doc-placement checker) re-anchored under `pypkg/src`.
3. **`__file__.parents[N]` anchors.** The fragile one. The package's ancestors
   each gained a level, so any `Path(__file__)...parents[N]` whose `N` reaches
   *past the package root* needs +1; anchors that stay inside the package are
   untouched. The rule is mechanical: for a file, `parents[depth]` is the
   package root (depth = its distance from the package root); `N > depth`
   escapes and gets +1; `N <= depth` is in-package and stays. `<pkg>.__file__`
   anchors are package-relative (depth 0), so any `N >= 1` escapes. This catches
   runtime anchors (a `default_data_root()` walking up to `.data`) as well as
   test anchors — the failure mode is silent (a CLI that stops finding `.data`,
   a test reading the wrong root), so it must be swept, not eyeballed.

## Procedure

1. **Dry-run.** `python arch-coherence/scripts/migrate_shape.py --repo <root>`
   prints the plan: detected shape, package name, and the count of pyproject
   settings / doc links / file anchors it will rewrite. A non-`src` shape is a
   no-op (idempotent).
2. **Apply.** Re-run with `--apply`. It performs the `git mv`s, rewrites all
   three reference classes, and re-installs the package editable at its new
   location (`pip install -e pypkg/src`).
3. **Gate.** It then runs `check_packaging` (shape is now `pypkg`) and
   `lint-imports` (contracts kept) and refuses to declare success on a broken
   tree. Run the project's own pre-commit suite before committing — the move
   touches docs and pyproject, which several hooks gate.
4. **Commit.** The reshape is one coherent commit: the renames plus the
   path-reference repairs, which are inseparable (the tree is broken without
   them).

## Edges and limits

- **One transition today.** `src` → `pypkg/src`. `pypkg` → `pypkg+djapp` is a
  *faces* move (adding a Django app) and belongs to `racecar-deploy`, not here.
- **The anchor rewrite is heuristic-free but assumes the parents-index idiom.**
  A repo-root walk done some other way (a `while not (p / ".git").exists()`
  loop, an env var) is not rewritten because it does not need to be. Code that
  hardcodes the literal string `"src/<pkg>"` in a path (rare) is not caught;
  the gate (imports + `check_packaging`) is the backstop.
- **Owner-authorized.** It relocates the build root and mutates working code.
  Not run on inferred consent; the dry-run is the default for exactly this
  reason.

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).
