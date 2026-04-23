## Purpose

Owns shared infrastructure used across all modules: enum definitions, audit mixin, security utilities, generic CRUD helpers, router factories, and application config.

This module does **not** contain business logic. If a function is specific to one domain (e.g., "validate that a WA code level matches this endpoint's scope"), it belongs in that module's service layer, not here.

---

## Non-obvious behavior

**`enums.py` is the single source of truth for all enum definitions.** All `StrEnum` classes are defined here and imported by models, schemas, and services. Never define an inline enum in a model file. This prevents circular imports and keeps enum values discoverable in one place.

**`AuditMixin` columns must be populated explicitly at the application layer.** The mixin provides `created_at`, `updated_at`, `created_by_id`, and `updated_by_id` columns. `updated_at` has an `onupdate` trigger at the SQLAlchemy level, but `created_by_id` and `updated_by_id` are plain nullable FK columns — they are not wired to the current user automatically. Every write endpoint is responsible for setting them. See `PATTERNS.md` §4 for the wiring pattern.

**`SYSTEM_USER_ID = 1` is defined in `config.py` and must be imported from there.** Never hardcode the integer `1` as a user ID in service code. Use `from app.common.config import SYSTEM_USER_ID`.

**`crud.py` provides two generic helpers:**
- `get_paginated_list()` — handles pagination, optional search, and sort for any model. Use this instead of hand-rolling list endpoints.
- `get_by_ids()` — fetches multiple records by a list of IDs with a single query and raises 404 if any are missing.

**`factories.py` provides two router factory functions:**
- `create_batch_import_router()` — generates a `POST /{resource}/batch/import` endpoint that accepts a CSV and bulk-inserts rows. Used by `schools/`, `contractors/`, `wa_codes/`, `deliverables/`.
- `create_readonly_router()` — generates a paginated `GET /` endpoint with built-in search (`?search=`) and generic column filters (`?col=val`). See `PATTERNS.md §15` for the full filter contract.

**`introspection.py` provides:**
- `filterable_columns(model)` — returns `{attr_name: Column}` for all scalar non-audit columns on a model. Called once at factory-construction time. Excludes `AuditMixin` fields by reading them directly from `AuditMixin.__annotations__`.

---

## Before you modify

- **Adding a new enum value** to any enum in `enums.py` is safe. Renaming or removing a value requires auditing all model columns that store it as a string (SQLite stores `StrEnum` values as plain strings; no DB-level constraint catches the mismatch until a query hits a stale row).
- **`AuditMixin` scope** is defined in `CLAUDE.md`. Do not apply it to `manager_project_assignments`, link tables, or the auth tables (`users`, `roles`, `permissions`).
- **`config.py`** reads from `.env` via `pydantic-settings`. Do not add runtime mutable state to `Settings`; it is instantiated once at import time.
