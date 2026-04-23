# Django Standards

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first

Django implies Python. For general Python conventions (naming, formatting, linting, CLI), see [PYTHON.md](PYTHON.md).

Service-layer separation and layered request flow apply [SYSTEM.md](SYSTEM.md) §3 Domain Boundaries and §4 Layered Dependency Graph at the framework level.

Sections are ordered as a DAG — most independent first, most dependent last.

## 1. Module Structure

How Django code is organized. Independent of runtime behavior.

**Service layer.** All business logic resides in `services/<service_name>.py` — not in views, not in models. The app stays a single deployable unit with clear internal module boundaries.

**Models.** Handle data persistence only. No business logic.

**Views.** Handle HTTP request/response only. Use Class-Based Views (CBVs). Use `LoginRequiredMixin` and `PermissionRequiredMixin` for access control.

## 2. Database & Performance

Runtime patterns. Depends on module structure being correct.

- **N+1 prevention.** Querysets must use `.select_related()` (FK/OneToOne) or `.prefetch_related()` (ManyToMany).
- **Timezone safety.** Never use `datetime.now()`. Use `django.utils.timezone.now`.
- **No heavy queries in model init.** Avoid database hits in Model `__init__` methods or properties.

## 3. Security

Cross-cutting concern. Depends on architecture and runtime patterns being sound.

- No secrets in code. Environment variables via `.env` / `os.environ`.
