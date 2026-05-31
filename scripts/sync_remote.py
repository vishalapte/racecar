#!/usr/bin/env python3
"""Sync canonical racecar check scripts from GitHub into an adopter repo.

Fetches the eight check scripts directly from the racecar GitHub repository
using urllib (stdlib — no pip required). Use this when you do not have a
local racecar clone and want to update an existing adopter repo to the latest
scripts (or a pinned ref).

Usage:
    # Fetch this script and run it in one step (no local clone needed):
    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest /path/to/repo

    # Pin to a specific tag or commit:
    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest /path/to/repo --ref v0.6.0

    # Preview without writing:
    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest /path/to/repo --dry-run

Exit codes: 0 always (sync is not a gate).
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

BASE_RAW = "https://raw.githubusercontent.com/vishalapte/racecar/{ref}/{path}"

CHECK_SCRIPTS = (
    "arch-coherence/scripts/check_upward_imports.py",
    "arch-coherence/scripts/check_cli_commands.py",
    "arch-coherence/scripts/check_packaging.py",
    "arch-coherence/scripts/check_dj_model_ref_as_string.py",
    "doc-coherence/scripts/check_docs.py",
    "doc-coherence/scripts/check_todo_format.py",
    "doc-coherence/scripts/check_claude_shape.py",
    "doc-coherence/scripts/check_file_placement.py",
)


def fetch(url: str) -> str:
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        return resp.read().decode("utf-8")


def sync(dest: Path, ref: str, dry_run: bool) -> None:
    """Fetch canonical scripts from GitHub and write them into dest/scripts/."""
    if not dest.is_dir():
        raise SystemExit(f"sync_remote: {dest} does not exist or is not a directory.")

    scripts_dir = dest / "scripts"
    created = updated = unchanged = 0

    for rel_source in CHECK_SCRIPTS:
        url = BASE_RAW.format(ref=ref, path=rel_source)
        try:
            canonical = fetch(url)
        except Exception as exc:
            print(f"  FETCH ERROR  {rel_source}: {exc}")
            continue

        target = scripts_dir / Path(rel_source).name

        if target.exists():
            if target.read_text(encoding="utf-8") == canonical:
                print(f"  unchanged  {target.relative_to(dest)}")
                unchanged += 1
                continue
            label = "updated"
            updated += 1
        else:
            label = "created"
            created += 1

        print(f"  {label:<9} {target.relative_to(dest)}")
        if not dry_run:
            scripts_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(canonical, encoding="utf-8")

    suffix = " (dry run — no files written)" if dry_run else ""
    print(
        f"sync_remote: {created} created, {updated} updated,"
        f" {unchanged} unchanged{suffix}"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Sync canonical racecar check scripts from GitHub into an adopter repo.",
    )
    p.add_argument(
        "--dest",
        type=Path,
        required=True,
        help="Root of the adopter repo (the directory containing its Makefile).",
    )
    p.add_argument(
        "--ref",
        default="main",
        help="Git ref (branch, tag, or commit SHA) to fetch from. Default: main.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing any files.",
    )
    return p


def main(argv: list[str]) -> int:
    args = parser().parse_args(argv)
    dest = args.dest.expanduser().resolve()
    sync(dest, ref=args.ref, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
