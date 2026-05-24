#!/usr/bin/env python3
"""SessionStart(compact) hook — prompt the agent to reconcile the decision log.

A hook runs a script, not agent reasoning, so it cannot itself write the
rich "why" entry. What it can do: after a compaction, inject an instruction
telling the resumed agent to mine the pre-compaction transcript (still on
disk at `transcript_path`) for decisions, rationale, rejected alternatives,
and gotchas not yet recorded in the project's `.claude/HISTORY.md`, and
append them. This is the Tier-3 judgment step, deterministically triggered
and fed by a deterministic pre-filter (the transcript) — the racecar
pattern: judgment only where a predicate can't decide, pre-filtered by what
a predicate can.

Companion to `precompact_history.py` (the deterministic marker). No-op
unless the project's `.claude/HISTORY.md` exists. Emits the SessionStart
`additionalContext` JSON on stdout; always exits 0.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _repo_root(start: Path) -> Path | None:
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    return None


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    cwd = data.get("cwd") or os.getcwd()
    transcript = data.get("transcript_path") or "the pre-compaction transcript"

    root = _repo_root(Path(cwd))
    if root is None:
        return 0
    history = root / ".claude" / "HISTORY.md"
    if not history.is_file():
        return 0  # opt-in

    message = (
        "Context was just compacted. Before continuing, reconcile the decision "
        f"log. Read the pre-compaction transcript at {transcript}, extract any "
        "decisions, rationale, rejected alternatives, or operational gotchas "
        f"that are not already in {history}, and append them under a dated "
        "entry (append-only — do not edit prior entries; a reversal is a new "
        "entry that says what changed and why). If everything material is "
        "already logged, say so briefly and move on. Then resume the task."
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": message,
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
