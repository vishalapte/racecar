# Django — Engineering Hygiene

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

Django-specific runtime and security hygiene. For Django architectural coherence (module structure, service-layer separation, view layering), see [`../arch-coherence/DJANGO.md`](../arch-coherence/DJANGO.md). For general Python hygiene, see [`PYTHON.md`](PYTHON.md).

## 1. Database & Performance

Runtime patterns.

- **N+1 prevention.** Querysets must use `.select_related()` (FK/OneToOne) or `.prefetch_related()` (ManyToMany).
- **Timezone safety.** Never use `datetime.now()`. Use `django.utils.timezone.now()`.
- **No database queries in `Model.__init__` or property accessors.**

## 2. Security

Cross-cutting concern.

- **No secrets in code.** Environment variables via `.env` / `os.environ`.
- **Access control on views.** Use `LoginRequiredMixin` and `PermissionRequiredMixin` on Class-Based Views. See [`../arch-coherence/DJANGO.md` §1 Module Structure](../arch-coherence/DJANGO.md#1-module-structure) for the CBV pattern this plugs into.

## 3. Linting

Ruff's `PL` rules cover the structural and logic portions of pylint, but ruff has no Django-aware rules. `pylint-django` fills that gap: it understands model fields, queryset types, and `get_user_model()` — things ruff cannot infer without a Django runtime.

**Django projects on the ruff variant must run both:**

```
ruff check src/          # structural + logic
pylint --load-plugins pylint_django src/   # Django-specific
```

Add to `pyproject.toml`:

```toml
[tool.pylint.main]
load-plugins = ["pylint_django"]

[tool.pylint."MESSAGES CONTROL"]
# Project-specific disables go here; keep this list short and justified.
# disable = []
```

The Definition of Done in [`PYTHON.md` §6](PYTHON.md#6-definition-of-done) covers the general ruff gate; this is an additional gate for Django projects only.
