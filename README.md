# Standards — Resolver

This is a routing table. Load the file that applies to the task at hand. Do not load all files.

Topic: Architectural coherence — four checks (acyclicity, direction, layer integrity, depth-plus-one isolation) with sub-axioms (environment-layer exception, domain boundaries), plus review lens
Load: [arch-coherence/README.md](arch-coherence/README.md)

Topic: Python architectural coherence — module structure, imports, CLI, enforcement
Load: [arch-coherence/PYTHON.md](arch-coherence/PYTHON.md)

Topic: Django architectural coherence — service layer, view layering
Load: [arch-coherence/DJANGO.md](arch-coherence/DJANGO.md)

Topic: Engineering review — wrapper around gstack `plan-eng-review` with racecar-specific pre/post passes
Load: [eng-review/README.md](eng-review/README.md)

Topic: Python engineering hygiene — mindset, naming, formatting, testing, linting, Definition of Done
Load: [eng-review/PYTHON.md](eng-review/PYTHON.md)

Topic: Django engineering hygiene — database/performance, security
Load: [eng-review/DJANGO.md](eng-review/DJANGO.md)

Topic: Documentation coherence — update protocol + review lens (links, section numbers, file naming, cogency, scope honesty, rule testability, one-home-per-rule)
Load: [doc-coherence/README.md](doc-coherence/README.md)

Topic: Ownership — tooling enables design and confirms correctness; responsibility stays with the owner
Load: [shared/OWNERSHIP.md](shared/OWNERSHIP.md)

Topic: Voice — shared conventions for prescriptive writing (standards and review outputs)
Load: [shared/VOICE.md](shared/VOICE.md)

Topic: TODO list rendering format
Load: [shared/TODO_FORMAT.md](shared/TODO_FORMAT.md)

Topic: Batching — operational discipline for agent execution (audit before fix, script mechanical changes, one verification cycle, parallel independent reads, group failure modes)
Load: [shared/BATCHING.md](shared/BATCHING.md)

Topic: Glossary — DAG, coherence, cogency, resolver, depth-plus-one, outward-downward, one-home-per-rule, scope honesty, drift
Load: [GLOSSARY.md](GLOSSARY.md)

Topic: Commits — Conventional Commits format, valid VERSION increments, VERSION bump convention
Load: [COMMITS.md](COMMITS.md)

## Enforcement

Reference this file from your project's `CLAUDE.md` or equivalent agent-instruction file. Read it first to find which component applies. Do not load component files speculatively — read only what the current task requires. If you arrived at a component file directly, return here first.

## Bootstrap check

After reading this file: verify that `~/.claude/settings.json` contains a `PostToolUse` hook entry whose `command` path ends with `hooks/claude_racecar_hook.sh`. If it is absent, prompt the user to add it (via `/update-config`) and run `make sync-claude-md`. Do not proceed silently.

## Pointer sync

`scripts/sync_claude_md.py` writes a managed block into `~/.claude/CLAUDE.md` (or `$CLAUDE_MD_PATH`) that points the local agent at this checkout. The script resolves its own location, so the path it writes is correct on whichever machine runs it. Run it any time the racecar checkout moves, or wire it to fire automatically.

Manual:

    make sync-claude-md

Auto (Claude Code hook). `hooks/claude_racecar_hook.sh` is the launcher — it reads the tool-call JSON on stdin, fires the sync only when `file_path` matches `*/racecar/README.md`, and always exits 0. Add this to `~/.claude/settings.json`, substituting the absolute path to your local racecar checkout:

    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Read",
            "hooks": [
              {
                "type": "command",
                "command": "/absolute/path/to/racecar/hooks/claude_racecar_hook.sh"
              }
            ]
          }
        ]
      }
    }

The path to the launcher is the only per-machine value. The block in `CLAUDE.md` is delimited by `<!-- BEGIN racecar pointer (managed) -->` / `<!-- END racecar pointer (managed) -->` and rewritten in place every run; content outside the markers is preserved.
