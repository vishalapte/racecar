---
name: racecar-deploy
description: Stand up REST + MCP web faces over a CLI-compliant project — the faces axis. Inserts an `api` cut vertex, scaffolds one Django project launched as two ASGI processes, one per face (REST on `api.*`, MCP on `mcp.*`), as thin adapters over `api`, and emits the Apache reverse-proxy vhosts. Stacks on `racecar-reshape` for its shape prerequisite: a web face needs the `pypkg+djapp` shape, so deploy invokes reshape (src -> pypkg/src) when the project is not there yet, then adds the djapp itself (pypkg -> pypkg+djapp). Write verbs are gated off by default. Generic and parameterized; no project-specific values baked in. Owner-authorized (api insertion mutates code), idempotent, regenerable. Use when asked to "expose the CLI as REST and MCP", "add a web face", "stand up the MCP server", "generate the REST API from the CLI", or "serve this behind Apache".
---

# racecar-deploy — REST + MCP web faces over one library

This skill is a routing pointer, not content. Load [`README.md`](README.md) for the full procedure.

The core: every CLI capability becomes reachable as REST and MCP **without re-implementing orchestration anywhere**, because all faces route through one `api` cut vertex ([`../arch-coherence/FACES.md`](../arch-coherence/FACES.md) §5). The generated Django app holds **zero orchestration**: each REST view and MCP tool handler translates transport input, calls `api`, renders. MCP is HTTP-delivered (Streamable HTTP), so it is a **route family in the web face, not a standalone `mcp.py`** — one Django project launched as two ASGI processes (one per face, each vhost selecting its settings module at boot), behind Apache.

**Two axes, stacked.** This skill owns the **faces axis** ([`../arch-coherence/FACES.md`](../arch-coherence/FACES.md), [`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md)): insert `api`, generate the web face, deliver behind Apache. The **shapes axis** prerequisite (`src` → `pypkg/src`) belongs to [`racecar-reshape`](../reshape/SKILL.md); a web face needs the `pypkg+djapp` shape, so this skill checks the shape and invokes `racecar-reshape` when needed, then adds the djapp itself. The user runs one command; the stacking is internal.

Owner-authorized: the `api` insertion mutates working code and is gated per change. Write verbs (any non-GET command) are OFF by default — enabled only by `RACECAR_WEB_FACE_ALLOW_WRITES=1` — so a no-tty face fails safe. Idempotent and regenerable: re-running re-derives the manifest and re-emits the faces; it never clobbers hand-edited orchestration in `api`.
