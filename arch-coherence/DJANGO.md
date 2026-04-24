# Django — Architectural Coherence

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

Django-specific architectural coherence — how the app layers. Django implies Python; for general Python coherence see [`PYTHON.md`](PYTHON.md). For Django engineering hygiene (database/performance, security), see [`../eng-review/DJANGO.md`](../eng-review/DJANGO.md). For the language-agnostic axioms, see [`README.md`](README.md).

Service-layer separation and layered request flow apply the [domain-boundaries](README.md#domain-boundaries) and [layer-integrity](README.md#3-layer-integrity) axioms at the framework level.

This file is intentionally sparse. Standards here are added only when a concrete pattern has emerged in the project; we do not manufacture content ahead of need.

## 1. Module Structure

How Django code is organized. Independent of runtime behavior.

**Service layer.** All business logic resides in `services/<service_name>.py` — not in views, not in models. The app stays a single deployable unit with clear internal module boundaries.

**Models.** Handle data persistence only. No business logic.

**Views.** Handle HTTP request/response only. Use Class-Based Views (CBVs). For access-control mixins on CBVs (`LoginRequiredMixin`, `PermissionRequiredMixin`), see [`../eng-review/DJANGO.md` §2 Security](../eng-review/DJANGO.md#2-security).
