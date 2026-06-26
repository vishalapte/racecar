---
name: racecar-reshape
description: Migrate a project between racecar packaging shapes (PACKAGING.md) — today src -> pypkg/src (the pypkg shape). The `git mv` is the easy 1%; the rest is repairing every path reference the move invalidates because the package sits one directory deeper, and each class has a deterministic rewrite — markdown doc links (relpath), pyproject path settings (setuptools where, ignore-paths re-anchor), and `__file__.parents[N]` anchors that escape the package (+1 to any N past the package root). Deterministic, idempotent (no-op if already pypkg), dry-run by default; owner-authorized because it relocates the build root and mutates code, and it gates on check_packaging + lint-imports before declaring success. This is the shapes-axis tool that `racecar-deploy` and `racecar-upgrade` both stack on. Use when asked to "reshape to pypkg", "nest src under pypkg/src", "move to pypkg shape", or as the prerequisite before adding a djapp / web face.
---

# racecar-reshape — packaging-shape migration

This skill is a routing pointer, not content. Load [`README.md`](README.md) for the full procedure.

The core: a packaging-shape change (`src` → `pypkg/src`) is a **path-rewrite migration, not a `git mv`**. Moving the package one directory deeper invalidates every reference that crossed the old boundary. There are exactly three classes, each with a deterministic repair (all learned on the gfem proving ground):

1. **Markdown doc links** — recompute with `os.path.relpath` to the resource's actual new location. Root-resource links gain a level; the library-pyproject link loses one (it moved *with* the package).
2. **pyproject path settings** — setuptools `where` `["src"]`→`["."]`; `[tool.pylint.MASTER].ignore-paths` (and peers) anchored at the old source root re-anchored under `pypkg/src`.
3. **`__file__.parents[N]` anchors** — +1 to any `N` that *escapes the package* (N greater than the file's depth to the package root); in-package anchors are untouched. This catches the runtime ones (e.g. a `default_data_root()` that walks up to `.data`) as well as test anchors.

The mechanism is [`../arch-coherence/scripts/migrate_shape.py`](../arch-coherence/scripts/migrate_shape.py): dry-run by default, `--apply` to perform it, then it gates on `check_packaging` + `lint-imports` and refuses to leave a broken tree. Idempotent: a project already at `pypkg`/`pypkg+djapp` is a no-op.

It owns only the **shapes axis** ([`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md)); it does not insert `api` or add faces. `racecar-deploy` stacks the faces axis on top; `racecar-upgrade` invokes this for the structural-uplift step. One home for the reshape.
