---
name: racecar-doctor
description: Verify that racecar is actually installed, wired, and loaded — layer by layer, deterministically. Use when asked "is racecar loaded?", "racecar doctor", "verify racecar install", "why isn't racecar loading", or any phrasing that questions whether the standards are present in the session.
---

# racecar-doctor

Answers "is racecar correctly installed and loaded here?" with evidence instead of a banner. The deterministic layers (files, wiring, hook execution, transcript) are checked by `scripts/doctor.py`; the probabilistic layer (is the model conditioning on the content) is checked by challenge-response against the load token.

## Step 1: locate the racecar checkout

Resolve the symlink at `~/.claude/skills/racecar-doctor`; the checkout root is one level up from `doctor/`. If the symlink does not exist, that is itself the first finding: report it and point at `./install` in the racecar checkout. Stop only if no checkout can be found at all.

## Step 2: run the deterministic check

    python3 <racecar_root>/scripts/doctor.py

Report the output verbatim — every `ok` / `FAIL` / `warn` line. Do not summarize failures away; each one names a file or a settings key.

## Step 3: layer-5 self-check (challenge-response)

The script prints `Expected load token: <hash>`. Now answer, **from context only — do not Read any racecar file**:

1. State the load token that was planted in this session's context by the standards loader.
2. State one substantive baseline rule (a specific rule from `shared/`, e.g. a COMMITS.md increment rule or an OPERATIONAL.md numbered rule).

Compare your token against the script's expected token:

- **Match** — the baseline entered this session's context and you are reading it. Report: layer 5 evidence positive. Label it honestly: this is an eval, not a proof; it raises confidence that the content is governing, it cannot guarantee it.
- **Mismatch** — the baseline in context is stale (checkout changed since session start). Report the mismatch; a fresh session (or `/clear`) re-injects.
- **Cannot produce a token** — the baseline is NOT in your context, whatever any banner said. Report layer 5 as failed even if layers 1-4 passed, and say which boundary was likely missed (e.g. session started before hooks were wired).

## Step 4: offer to fix

If layers 1 or 2 had failures, offer:

    python3 <racecar_root>/scripts/doctor.py --fix

`--fix` re-runs `sync_claude_md.py` (rewrites the managed hooks and pointer block) and creates only **missing** symlinks — anything present-but-wrong is refused, never clobbered, same as `./install`. Run it only with the user's consent, then re-run Step 2 and report the delta. Wiring fixes take effect at the next session boundary; say so.

## Output discipline

One consolidated report: the four deterministic layers verbatim, then the layer-5 verdict with the token comparison. No banner, no "everything looks good" without the lines that prove it. A `warn` on layer 4 is honest uncertainty, not a failure — explain it in one sentence.
