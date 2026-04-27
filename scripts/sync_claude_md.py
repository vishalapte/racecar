#!/usr/bin/env python3
"""Sync a racecar pointer block into ~/.claude/CLAUDE.md.

Writes (and rewrites) a managed block in the target CLAUDE.md so the local
agent loads racecar from this checkout's path. Idempotent: every run
replaces the block in-place. Designed to be invoked manually (Makefile)
or automatically (Claude Code PostToolUse hook on Read of
`racecar/README.md`).

Discovery:
  - RACECAR_ROOT is the parent directory of `scripts/`, computed from this
    file's own location. Works regardless of where racecar is cloned on
    this machine.
  - Target defaults to `~/.claude/CLAUDE.md`. Override with `--target` or
    the `CLAUDE_MD_PATH` env var.

Block markers:
  <!-- BEGIN racecar pointer (managed) -->
  ...
  <!-- END racecar pointer (managed) -->

Anything outside the markers is preserved untouched. If the target file
does not exist it is created. If the markers are missing the block is
appended (with a leading blank line).

Usage:
    python3 <racecar>/scripts/sync_claude_md.py
    python3 <racecar>/scripts/sync_claude_md.py --dry-run
    python3 <racecar>/scripts/sync_claude_md.py --target /path/to/CLAUDE.md
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BEGIN_MARKER = "<!-- BEGIN racecar pointer (managed) -->"
END_MARKER = "<!-- END racecar pointer (managed) -->"

RACECAR_ROOT = Path(__file__).resolve().parent.parent


def render_block(racecar_root: Path) -> str:
    readme = racecar_root / "README.md"
    batching = racecar_root / "shared" / "BATCHING.md"
    return (
        f"{BEGIN_MARKER}\n"
        f"## Standards: racecar\n"
        f"Load `{readme}` as the resolver for any task involving code review, "
        f"architectural coherence, documentation drift, or Python/Django "
        f"engineering hygiene. Read it first to find which component file "
        f"applies; do not load component files speculatively.\n\n"
        f"Execution discipline (audit before fix, script mechanical changes, "
        f"one verification cycle, parallel independent reads, group failure "
        f"modes by root cause): `{batching}`.\n"
        f"{END_MARKER}\n"
    )


def replace_or_append(existing: str, block: str) -> str:
    if BEGIN_MARKER in existing and END_MARKER in existing:
        before, _, rest = existing.partition(BEGIN_MARKER)
        _, _, after = rest.partition(END_MARKER)
        # Drop the trailing newline that followed the END marker so the
        # rewrite produces the same shape every run.
        if after.startswith("\n"):
            after = after[1:]
        return f"{before}{block}{after}"
    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    if not existing:
        return block
    return f"{existing}{separator}{block}"


def resolve_target(arg_target: str | None) -> Path:
    if arg_target:
        return Path(arg_target).expanduser().resolve()
    env_target = os.environ.get("CLAUDE_MD_PATH")
    if env_target:
        return Path(env_target).expanduser().resolve()
    return (Path.home() / ".claude" / "CLAUDE.md").resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--target",
        help="Path to CLAUDE.md (default: $CLAUDE_MD_PATH or ~/.claude/CLAUDE.md).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resulting file to stdout instead of writing.",
    )
    args = parser.parse_args()

    target = resolve_target(args.target)
    block = render_block(RACECAR_ROOT)
    existing = target.read_text() if target.exists() else ""
    updated = replace_or_append(existing, block)

    if args.dry_run:
        sys.stdout.write(updated)
        return 0

    if updated == existing:
        print(f"sync_claude_md: {target} already up to date")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(updated)
    action = "updated" if existing else "created"
    print(f"sync_claude_md: {action} {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
