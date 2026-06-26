# racecar-deploy — the procedure

Accessed via [`SKILL.md`](SKILL.md). Doctrine homes this skill executes against:
[`FACES.md`](../arch-coherence/FACES.md) (the `lib → api → faces` axis),
[`PACKAGING.md`](../arch-coherence/PACKAGING.md) (the shapes axis),
[`CLI.md`](../arch-coherence/CLI.md) (the compliant format this reads from).

## What this skill is for

One library, exposed through N faces. The CLI already exists. This skill adds two
more faces — a REST API and an MCP server — and makes all three route through one
`api` vertex so orchestration has exactly one home. The faces are generated from
the CLI's own audit tree; nothing is hand-restated.

It is built to run **across many projects**: every step is parameterized by the
package name `<pkg>` and the vertical names, and reads the project's shape off disk
(PACKAGING.md §"How the shape is determined"). No project-specific value is baked in.

## What this skill owns (faces axis), and what it stacks on

This skill owns the **faces axis**: the `api` cut-vertex insertion (step 3) and the
web-face generation + delivery (steps 2, 4–6). It does **not** own the shapes axis.
The `src` → `pypkg/src` shape migration is [`racecar-reshape`](../reshape/SKILL.md)'s
job; deploy **stacks on it** — step 1 invokes reshape when the project is not yet
`pypkg`. [`racecar-upgrade`](../upgrade/SKILL.md) reuses `racecar-reshape` for its
structural uplift too: one home for the move, two skills compose it.

What this skill does *not* own: the shape migration ([`racecar-reshape`](../reshape/SKILL.md));
the general drift-classification and Makefile-fold work ([`racecar-upgrade`](../upgrade/SKILL.md));
the import-graph gate ([`racecar-arch-coherence`](../arch-coherence/SKILL.md)). It
calls those, it does not reimplement them.

## Preconditions

- The project is racecar-CLI-compliant: each `__main__.py` exposes `commands()` /
  `subcommands()` / `parser()` and `check_cli_commands.py --json <pkg>` emits a clean
  enriched tree (CLI.md). **The audit tree is the exposure spec and the arg schema.**
- The CLI surface is the curated allow-list of what gets exposed. A capability not
  reachable from the CLI is not exposed by REST or MCP. Widening exposure is a
  deliberate CLI registration, not a side effect of this skill.

## The pipeline

Each step is mechanical. Steps 1 and 3 mutate working code and are **owner-gated**
(per-change signoff). Everything else is regenerable and idempotent.

### 1. Reach the `pypkg+djapp` shape — *via racecar-reshape (gated)*

A Django web face requires the `pypkg+djapp` shape. Read the current shape off disk
(PACKAGING.md §"How the shape is determined"):

- If the project is `src`-shape, invoke [`racecar-reshape`](../reshape/SKILL.md) to do
  `src` → `pypkg/src`. Its [`migrate_shape.py`](../arch-coherence/scripts/migrate_shape.py)
  performs the `git mv` and repairs the three path-reference classes the move
  invalidates (doc links, pyproject settings, `__file__.parents[N]` anchors). Deploy
  does not reimplement this.
- If already `pypkg` or `pypkg+djapp`, reshape is a no-op (idempotent).

Step 1 gets the project to `pypkg`; this skill adds the djapp itself (step 2), taking
it to `pypkg+djapp`. `racecar.mk` re-derives `SRC` / `PKG` / `DJAPP` from the on-disk
markers — no edit.

### 2. Create the `djapp/` web face if absent

The Django ASGI project, rendered by `scaffold_web_face.py` from the manifest
(§4) — **vertical-first**: one Django app per vertical under `apps/<v>/`, plus a
`project/` composition root:

- `djapp/manage.py` (the shape marker that makes it `pypkg+djapp`).
- `djapp/pyproject.toml` from `templates/classic/djapp-pyproject.toml` — **no
  `[project]` block, no `[build-system]`** (PACKAGING.md §"djapp pyproject"); it runs
  via `manage.py`, it is not a wheel.
- `djapp/project/asgi.py` — the single ASGI entrypoint (not `wsgi.py`; see Delivery);
  each process picks its face's settings at boot.
- `djapp/project/settings/{settings,api,mcp}.py`, `project/urls/{apiurls,mcpurls}.py`,
  `project/faceguard.py`, `project/views.py` (serves the OpenAPI doc),
  `project/sitemaps.py`.
- `djapp/apps/<v>/` per vertical: `commands.py` (the transport-neutral binding),
  `views/{apiviews,mcpviews}.py`, `urls/apiurls.py`, and a Django app stub
  (`apps.py`, `models.py`, `admin.py`).
- `djapp/apps/mcp.py` — the single MCP Streamable-HTTP endpoint, unioning every
  vertical's `mcpviews.TOOLS`.
- The `django` dependency group (PACKAGING.md §"Shape-specific sidecar groups"):
  `django` + `uvicorn` at runtime, `openapi-spec-validator` to validate the
  generated OpenAPI doc (§5). There is **no** `drf-spectacular` and no DRF — the
  OpenAPI document is generated from the manifest, not introspected from views.

The djapp imports the installable `<pkg>` and holds zero orchestration.

### 3. Insert the `api` cut vertex per vertical — *gated*

Today the CLI reaches into the lib directly. Insert `api.py` between them so every
face routes through it (FACES.md §5, the articulation point):

- For each vertical, create `<pkg>/<verb>/api.py` and move orchestration into it —
  input resolution, credential seeding, defaulting, dispatch — out of `__main__.py`.
- Thin the CLI: `__main__.py` now translates argparse input, calls `api`, renders.
- Add the one `layers` contract to `[tool.importlinter]` (FACES.md §4). Run
  `lint-imports` → `Contracts: N kept, 0 broken`. A break names a sibling-vertical
  cross-import or an upward import; fix the structure.
- Run `check_face_orchestration.py` (advisory) — a non-classifiable vertical or a
  declared-`api` that is not the cut vertex is a Finding to resolve before generating.

`api` is the **bind target** for the generated faces. The faces call `api`
functions; nothing subprocesses `python -m`.

### 4. Build the Interface Manifest

The generation seam: one derived JSON binding each exposed command to its `api`
callable and its arg schema. Built from two sources, one home each:

- **Exposure set + arg schema** — the CLI audit tree (`check_cli_commands.py --json`).
  Its `oneOf` arg shape is already JSON-Schema (CLI.md §"mutex groups borrow oneOf"),
  which is what both OpenAPI parameters and MCP `inputSchema` consume.
- **Call target** — the `api` callable for each command, with the arg→parameter
  mapping.

The manifest is derived, never hand-maintained. Its formal IR spec, the binding
format, and the api-vs-argparse schema-source reconciliation are the doctrine in
[`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md).

### 5. Generate the two faces, co-located per vertical

Both are thin Django adapters over `api`, emitted from the manifest. Each vertical
holds both: `apps/<v>/commands.py` is the single transport-neutral binding, and the
two faces are **siblings over it** (mcp never imports the REST face):

- **REST** on `api.*` — `apps/<v>/views/apiviews.py` built from `commands`, mounted
  by `project/urls/apiurls.py` under the versioned taxonomy
  `/api/v1/<package>/<vertical-path>/<command>` (the vertical's full dotted name;
  `gfem.data.ercot list` → `/api/v1/gfem/data/ercot/list`). Args map to query/body
  parameters; `oneOf` carries through unchanged. The OpenAPI 3.1.0 document is built
  from the manifest (validated by `openapi-spec-validator`) and served from
  `project/views.py` at `/api/v1/openapi.json`.
- **MCP** on `mcp.*` — `apps/<v>/views/mcpviews.py` builds each vertical's `TOOLS`
  table; `apps/mcp.py` unions them behind one Streamable HTTP endpoint exposing one
  MCP tool per command, each command's arg schema becoming the tool's `inputSchema`.

> Verify the current MCP Streamable HTTP transport spec before emitting the MCP
> endpoint. Do not assume the request/response and SSE-upgrade contract from memory.

Each view/handler translates, calls `api`, renders. No re-resolution, no defaulting,
no credential handling in the face (FACES.md §9, the placement principle).

The same manifest also renders the generated docs in `djapp/docs/api/`
(`manifest.json`, `openapi.json`, `ENDPOINTS.md`) plus a `/sitemap/` of the GET
surface, so the spec never drifts from the routes. GENERATION.md §"Generated API
docs" is the doctrine. There is no `web/` directory.

### 6. Emit Apache delivery

Host-based virtual hosts (the default; path-based is the no-subdomain fallback):

```
Apache (TLS + name-based vhosts: api.* , mcp.* )
   ├─ api.*  ─ mod_proxy_http ─> uvicorn :8001  (DJANGO_SETTINGS_MODULE=project.settings.api)
   └─ mcp.*  ─ mod_proxy_http ─> uvicorn :8002  (DJANGO_SETTINGS_MODULE=project.settings.mcp)
         one Django project (project/asgi.py), two processes; each settings
         module fixes ROOT_URLCONF to its face's urlconf
```

One Django project, launched as **two processes** — one per face. `django.conf.settings`
is a process-global singleton, so the host split is per-process at **boot**
(`DJANGO_SETTINGS_MODULE` per vhost → `ROOT_URLCONF` per face), not a per-request
`request.get_host()` check. A `faceguard` middleware attaches `request.face` and
`404`s a wrong-face host, but never swaps the urlconf. The skill emits the two vhost
snippets and `run.sh` (both uvicorns); it does not own TLS material or DNS.

**Why ASGI, not mod_wsgi.** The MCP ecosystem is async-native and LLM-facing traffic
is slow-I/O-bound and SSE-capable; mod_wsgi pins a worker thread per in-flight
request and handles SSE badly. Apache stays as the TLS-terminating reverse proxy;
each face runs as its own ASGI (uvicorn) process, so MCP can grow SSE without
touching REST.

## Idempotence and re-runs

Steps 4–6 are regenerable: re-running re-derives the manifest and re-emits the
per-vertical `commands`/views/urls, the `apps/mcp.py` endpoint, the `project/`
composition root, the generated docs (`docs/api/{manifest,openapi}.json`,
`ENDPOINTS.md`), and the vhost snippets. It **never clobbers hand-edited
orchestration in `api`** — that is the one place humans own. Steps 1–3 are
one-time structural moves; a project already past them skips them.

## Gated points (owner signoff)

- Step 1 (the shape migration) is owner-gated but owned by [`racecar-reshape`](../reshape/SKILL.md)
  (it relocates the build root). Step 3 (api insertion) mutates working code and is
  gated here — per-change signoff, never on inferred consent.
- Steps 2, 4, 5, 6 are additive scaffolding and generation; idempotent, no signoff
  beyond the initial engage.
