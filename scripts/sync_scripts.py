#!/usr/bin/env python3
"""Sync canonical racecar check scripts into an existing adopter repo.

Copies the eight check scripts from their canonical racecar homes into
<dest>/scripts/<basename>.py. Scripts that are already up-to-date are left
untouched. Scripts that differ are overwritten; new scripts are created.

Use this when racecar updates a check script and you want the adopter repo
to pick up the change without re-running the full scaffolder (which refuses
non-empty destinations).

Usage:
    python scripts/sync_scripts.py --dest /path/to/repo
    python scripts/sync_scripts.py --dest /path/to/repo --dry-run
    python scripts/sync_scripts.py --dest /path/to/repo --templates  # + missing templates

    # Via Make (from racecar root):
    make sync-scripts DEST=/path/to/repo
    make sync-scripts DEST=/path/to/repo DRY_RUN=--dry-run

Exit codes: 0 always (sync is not a gate).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Scripts synced to every adopter repo.
CHECK_SCRIPTS = (
    "arch-coherence/scripts/check_upward_imports.py",
    "arch-coherence/scripts/check_cli_commands.py",
    "arch-coherence/scripts/check_packaging.py",
    "doc-coherence/scripts/check_docs.py",
    "doc-coherence/scripts/check_todo_format.py",
    "doc-coherence/scripts/check_claude_shape.py",
    "doc-coherence/scripts/check_file_placement.py",
    "scripts/clean_files.sh",
)

# Scripts synced only when the dest repo contains a manage.py (Django project).
DJANGO_SCRIPTS = ("arch-coherence/scripts/check_dj_model_ref_as_string.py",)

# Scripts that were renamed; removed from dest/scripts/ on sync to avoid stale copies.
REMOVED_SCRIPTS = ("check_string_relations.py",)

# Templates delivered create-if-missing only (--templates). Existing copies are
# never overwritten: templates are per-project-customized example artifacts,
# not canon — drift in an existing Makefile is check_packaging.py's to report,
# not sync's to clobber. (source relative to racecar root, target relative to dest)
TEMPLATE_FILES = (
    ("templates/classic/Makefile", "Makefile"),
    ("templates/classic/pre-commit-config.yaml", ".pre-commit-config.yaml"),
    ("templates/classic/gitignore", ".gitignore"),
    ("templates/classic/install_system_deps.sh", "scripts/install_system_deps.sh"),
)


def _is_django_repo(dest: Path) -> bool:
    return any(dest.rglob("manage.py"))


def _sync_one(source: Path, target: Path, dry_run: bool) -> str:
    """Write source to target if changed. Returns 'created', 'updated', or 'unchanged'."""
    canonical = source.read_text(encoding="utf-8")
    if target.exists():
        if target.read_text(encoding="utf-8") == canonical:
            return "unchanged"
        label = "updated"
    else:
        label = "created"
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonical, encoding="utf-8")
    return label


def _sync_templates(dest: Path, dry_run: bool) -> int:
    """Create-if-missing template delivery. Returns count created."""
    created = 0
    for rel_source, rel_target in TEMPLATE_FILES:
        source = REPO_ROOT / rel_source
        if not source.exists():
            print(f"  MISSING in racecar: {rel_source} (skipped)")
            continue
        target = dest / rel_target
        if target.exists():
            print(f"  exists     {rel_target}  (templates are never overwritten)")
            continue
        note = "  — set the shape variables" if rel_target == "Makefile" else ""
        print(f"  created    {rel_target}  (from {rel_source}{note})")
        created += 1
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            if rel_target.endswith(".sh"):
                target.chmod(target.stat().st_mode | 0o111)
    return created


def sync(dest: Path, dry_run: bool, templates: bool = False) -> None:
    """Copy canonical scripts into dest/scripts/, reporting each outcome."""
    if not dest.is_dir():
        raise SystemExit(f"sync_scripts: {dest} does not exist or is not a directory.")

    scripts_dir = dest / "scripts"
    is_django = _is_django_repo(dest)
    created = updated = unchanged = removed = 0

    all_scripts = list(CHECK_SCRIPTS) + (list(DJANGO_SCRIPTS) if is_django else [])
    for rel_source in all_scripts:
        source = REPO_ROOT / rel_source
        if not source.exists():
            print(f"  MISSING in racecar: {rel_source} (skipped)")
            continue
        target = scripts_dir / Path(rel_source).name
        label = _sync_one(source, target, dry_run)
        print(f"  {label:<9} {target.relative_to(dest)}")
        if label == "created":
            created += 1
        elif label == "updated":
            updated += 1
        else:
            unchanged += 1

    for old_name in REMOVED_SCRIPTS:
        old = scripts_dir / old_name
        if old.exists():
            print(f"  removed    scripts/{old_name}  (renamed)")
            removed += 1
            if not dry_run:
                old.unlink()

    templates_created = _sync_templates(dest, dry_run) if templates else 0

    suffix = " (dry run — no files written)" if dry_run else ""
    parts = [f"{created} created", f"{updated} updated", f"{unchanged} unchanged"]
    if removed:
        parts.append(f"{removed} removed")
    if templates:
        parts.append(f"{templates_created} template(s) created")
    print(f"sync_scripts: {', '.join(parts)}{suffix}")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Sync canonical racecar check scripts into an existing adopter repo.",
    )
    p.add_argument(
        "--dest",
        type=Path,
        required=True,
        help="Root of the adopter repo (the directory containing its Makefile).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing any files.",
    )
    p.add_argument(
        "--templates",
        action="store_true",
        help="Also deliver missing template files (Makefile, .pre-commit-config.yaml, "
        ".gitignore, scripts/install_system_deps.sh). Create-if-missing only; "
        "existing files are never overwritten.",
    )
    return p


def main(argv: list[str]) -> int:
    args = parser().parse_args(argv)
    dest = args.dest.expanduser().resolve()
    sync(dest, dry_run=args.dry_run, templates=args.templates)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
