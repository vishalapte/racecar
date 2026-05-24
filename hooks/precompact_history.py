#!/usr/bin/env python3
"""PreCompact hook — append a deterministic compaction marker.

Claude Code passes PreCompact JSON on stdin (cwd, trigger, ...) before it
summarizes the conversation. We locate the git repo root above `cwd`; if
`<root>/.claude/HISTORY.md` exists (the project opted into the decision-log
convention), append a timestamped marker recording *where* a compaction
happened — branch, short HEAD, trigger (manual/auto). The same marker is
mirrored to `~/.claude/history/<repo-kebab>.md`.

This is the Tier-2 deterministic half: it records the spine. It does NOT
write the rich "why" entry — that needs agent judgment and is prompted by
the SessionStart(compact) companion hook, which fires after compaction and
points the agent at the still-on-disk transcript.

No-op (and silent) unless the project's `.claude/HISTORY.md` exists. Always
exits 0 — a hook must never block compaction.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _repo_root(start: Path) -> Path | None:
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    return None


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _mirror_path(root: Path) -> Path:
    kebab = re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-") or "repo"
    mirror_dir = Path.home() / ".claude" / "history"
    mirror_dir.mkdir(parents=True, exist_ok=True)
    return mirror_dir / f"{kebab}.md"


def _append(path: Path, text: str) -> None:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    cwd = data.get("cwd") or os.getcwd()
    trigger = data.get("trigger") or "compact"

    root = _repo_root(Path(cwd))
    if root is None:
        return 0
    history = root / ".claude" / "HISTORY.md"
    if not history.is_file():
        return 0  # opt-in: project hasn't adopted the decision log

    ts = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    head = _git(root, "rev-parse", "--short", "HEAD") or "?"
    marker = f"\n> ⟳ context compacted {ts} · {branch}@{head} · trigger={trigger}\n"

    _append(history, marker)
    _append(_mirror_path(root), marker)
    return 0


if __name__ == "__main__":
    sys.exit(main())
