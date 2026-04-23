# Standards — Resolver

This is a routing table. Load the file that applies to the task at hand. Do not load all files.

| Topic | Load |
|-------|------|
| Architectural axioms — dependency direction, no circular dependencies, domain boundaries, layered graph, entry points | [core/SYSTEM.md](core/SYSTEM.md) |
| Documentation update protocol | [core/DOCS.md](core/DOCS.md) |
| TODO list rendering format | [core/TODO.md](core/TODO.md) |
| Python standards — dev strategy, naming, formatting, testing, module structure, imports, linting, CLI pattern, Definition of Done | [python/PYTHON.md](python/PYTHON.md) |
| Django — service layer, views, database, security | [python/DJANGO.md](python/DJANGO.md) |
| Enforcement of SYSTEM.md via import-linter + pre-commit | [python/PYTHON.md §10](python/PYTHON.md#10-enforcement) |
| Code review lens — seven checks, red flags, decision patterns, voice | [CRITIC.md](CRITIC.md) |

## Enforcement

Reference this file from your project's `CLAUDE.md` or equivalent agent-instruction file. Read it first to find which component applies. Do not load component files speculatively — read only what the current task requires. If you arrived at a component file directly, return here first.
