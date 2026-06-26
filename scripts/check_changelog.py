#!/usr/bin/env python3
"""Assert CHANGELOG.md's newest entry matches VERSION.

racecar's own `make check` runs this so the changelog cannot silently drift behind
VERSION. The packaging-rule changelog check (check_packaging_rules/_changelog) only
verifies that an adopter's changelog has a valid Keep-a-Changelog header; this is
the stricter self-check racecar holds itself to: every version bump ships a matching
top entry, so the per-version record never falls behind the code.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# A released entry: `## X.Y.Z - YYYY-MM-DD` (the `## [Unreleased]` placeholder that a
# fresh changelog may carry is intentionally NOT matched, since it has no version).
_ENTRY_RE = re.compile(
    r"^## (\d+\.\d+\.\d+(?:[-+][\w.-]+)?) - \d{4}-\d{2}-\d{2}", re.MULTILINE
)


def newest_changelog_version(changelog: str) -> str | None:
    """Return the version of the newest released CHANGELOG.md entry, or None."""
    match = _ENTRY_RE.search(changelog)
    return match.group(1) if match else None


def problem(root: Path) -> str | None:
    """Return an error message if VERSION and the newest changelog entry disagree."""
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    changelog_path = root / "CHANGELOG.md"
    if not changelog_path.exists():
        return "CHANGELOG.md is missing"
    top = newest_changelog_version(changelog_path.read_text(encoding="utf-8"))
    if top is None:
        return "no released `## X.Y.Z - YYYY-MM-DD` entry found in CHANGELOG.md"
    if top != version:
        return (
            f"VERSION is {version} but the newest CHANGELOG.md entry is {top}; "
            f"add a {version} entry"
        )
    return None


def main() -> int:
    """CLI entry: 0 when the changelog leads with VERSION, 1 otherwise."""
    err = problem(REPO_ROOT)
    if err:
        print(f"check_changelog: {err}", file=sys.stderr)
        return 1
    print("check_changelog: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
