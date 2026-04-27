#!/usr/bin/env python3
"""Sync racecar bootstrap into the local Claude Code config.

Two idempotent operations against `~/.claude/`:

1. Pointer block in `~/.claude/CLAUDE.md` — a managed `<!-- BEGIN/END
   racecar pointer -->` block that points the agent at this checkout.
2. Hooks in `~/.claude/settings.json` — a `PostToolUse` Read hook
   (`hooks/claude_racecar_hook.sh`) and a `PreToolUse` Bash hook
   (`hooks/compound-command-allow.sh`), both wired to absolute paths
   inside this checkout.

Every run rewrites both in place. Designed to be invoked manually
(Makefile) or automatically (Claude Code PostToolUse hook on Read of
`racecar/README.md`).

Discovery:
  - RACECAR_ROOT is the parent directory of `scripts/`, computed from
    this file's own location. Works regardless of where racecar is
    cloned on this machine.
  - CLAUDE.md target defaults to `~/.claude/CLAUDE.md`. Override with
    `--claude-md` or `CLAUDE_MD_PATH`.
  - settings.json target defaults to `~/.claude/settings.json`.
    Override with `--settings` or `CLAUDE_SETTINGS_PATH`.

Block markers (CLAUDE.md):
  <!-- BEGIN racecar pointer (managed) -->
  ...
  <!-- END racecar pointer (managed) -->

Hook identification (settings.json): an existing hook entry whose
`command` ends with the same script basename is treated as racecar's
and rewritten in place. Other hooks at the same matcher are preserved.

Usage:
    python3 <racecar>/scripts/sync_claude_md.py
    python3 <racecar>/scripts/sync_claude_md.py --dry-run
    python3 <racecar>/scripts/sync_claude_md.py --claude-md /path/to/CLAUDE.md
    python3 <racecar>/scripts/sync_claude_md.py --settings /path/to/settings.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

BEGIN_MARKER = "<!-- BEGIN racecar pointer (managed) -->"
END_MARKER = "<!-- END racecar pointer (managed) -->"

RACECAR_ROOT = Path(__file__).resolve().parent.parent

POST_HOOK_BASENAME = "claude_racecar_hook.sh"
PRE_HOOK_BASENAME = "compound-command-allow.sh"


# --- CLAUDE.md pointer block -------------------------------------------------


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
        if after.startswith("\n"):
            after = after[1:]
        return f"{before}{block}{after}"
    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    if not existing:
        return block
    return f"{existing}{separator}{block}"


# --- settings.json hooks -----------------------------------------------------


def upsert_hook(
    settings: dict[str, Any],
    event: str,
    matcher: str,
    command: str,
    basename: str,
) -> bool:
    """Ensure `settings.hooks[event]` has a matcher entry containing `command`.

    A racecar-managed hook is identified by its command ending in `basename`
    (with optional whitespace/quotes), allowing us to rewrite a stale path
    without disturbing unrelated hooks. Returns True if the settings dict
    was mutated.
    """
    hooks_root = settings.setdefault("hooks", {})
    if not isinstance(hooks_root, dict):
        raise ValueError(f"settings.json `hooks` is not an object: {type(hooks_root).__name__}")

    event_entries = hooks_root.setdefault(event, [])
    if not isinstance(event_entries, list):
        raise ValueError(f"settings.json `hooks.{event}` is not an array")

    matcher_entry: dict[str, Any] | None = None
    for entry in event_entries:
        if isinstance(entry, dict) and entry.get("matcher") == matcher:
            matcher_entry = entry
            break

    created_matcher = False
    if matcher_entry is None:
        matcher_entry = {"matcher": matcher, "hooks": []}
        event_entries.append(matcher_entry)
        created_matcher = True

    inner = matcher_entry.setdefault("hooks", [])
    if not isinstance(inner, list):
        raise ValueError(f"settings.json `hooks.{event}[matcher={matcher}].hooks` is not an array")

    desired = {"type": "command", "command": command}

    for h in inner:
        if not isinstance(h, dict):
            continue
        cmd = h.get("command", "")
        if isinstance(cmd, str) and cmd.rstrip().rstrip('"').rstrip("'").endswith(basename):
            if h == desired:
                return created_matcher
            h.clear()
            h.update(desired)
            return True

    inner.append(desired)
    return True


def sync_settings(
    racecar_root: Path,
    settings_path: Path,
    *,
    dry_run: bool,
) -> tuple[bool, str]:
    """Upsert both hooks into settings.json. Returns (changed, rendered_text)."""
    pre_command = str(racecar_root / "hooks" / PRE_HOOK_BASENAME)
    post_command = str(racecar_root / "hooks" / POST_HOOK_BASENAME)

    if settings_path.exists():
        raw = settings_path.read_text()
        try:
            settings = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as e:
            raise SystemExit(f"sync_claude_md: cannot parse {settings_path}: {e}")
    else:
        raw = ""
        settings = {}

    if not isinstance(settings, dict):
        raise SystemExit(f"sync_claude_md: {settings_path} top-level value is not a JSON object")

    pre_changed = upsert_hook(settings, "PreToolUse", "Bash", pre_command, PRE_HOOK_BASENAME)
    post_changed = upsert_hook(settings, "PostToolUse", "Read", post_command, POST_HOOK_BASENAME)

    rendered = json.dumps(settings, indent=2) + "\n"
    changed = pre_changed or post_changed or (rendered != raw)

    if changed and not dry_run:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(rendered)

    return changed, rendered


# --- target resolution -------------------------------------------------------


def resolve_path(arg: str | None, env: str, default: Path) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env_value = os.environ.get(env)
    if env_value:
        return Path(env_value).expanduser().resolve()
    return default.resolve()


# --- entry point -------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--claude-md",
        "--target",
        dest="claude_md",
        help="Path to CLAUDE.md (default: $CLAUDE_MD_PATH or ~/.claude/CLAUDE.md).",
    )
    parser.add_argument(
        "--settings",
        help="Path to settings.json (default: $CLAUDE_SETTINGS_PATH or ~/.claude/settings.json).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resulting files to stdout instead of writing.",
    )
    args = parser.parse_args()

    claude_md = resolve_path(args.claude_md, "CLAUDE_MD_PATH", Path.home() / ".claude" / "CLAUDE.md")
    settings_path = resolve_path(
        args.settings, "CLAUDE_SETTINGS_PATH", Path.home() / ".claude" / "settings.json"
    )

    block = render_block(RACECAR_ROOT)
    existing_md = claude_md.read_text() if claude_md.exists() else ""
    updated_md = replace_or_append(existing_md, block)

    settings_changed, rendered_settings = sync_settings(
        RACECAR_ROOT, settings_path, dry_run=args.dry_run
    )

    if args.dry_run:
        sys.stdout.write(f"--- {claude_md} ---\n")
        sys.stdout.write(updated_md)
        sys.stdout.write(f"\n--- {settings_path} ---\n")
        sys.stdout.write(rendered_settings)
        return 0

    md_changed = updated_md != existing_md
    if md_changed:
        claude_md.parent.mkdir(parents=True, exist_ok=True)
        claude_md.write_text(updated_md)
        print(f"sync_claude_md: {'created' if not existing_md else 'updated'} {claude_md}")
    else:
        print(f"sync_claude_md: {claude_md} already up to date")

    if settings_changed:
        print(f"sync_claude_md: updated hooks in {settings_path}")
    else:
        print(f"sync_claude_md: {settings_path} hooks already up to date")

    return 0


if __name__ == "__main__":
    sys.exit(main())
