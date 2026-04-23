# Session Handoff — 2026-04-23 (Phase 1.7 complete)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Phase 1.7 complete and fully tested.** Every factory-backed `GET /[entity]` endpoint now supports generic column-filter query params.

---

## What Was Done This Session

Implemented Phase 1.7 — generic column filtering in `create_readonly_router`.

**Files created/modified:**

- `app/common/introspection.py` *(new)* — `filterable_columns(model)` helper. Iterates `mapper.iterate_properties`, skips non-`ColumnProperty` attrs, excludes `AuditMixin` fields (derived dynamically from `AuditMixin.__annotations__`, not a hardcoded list), excludes columns whose type has no `python_type`. Returns `{attr_name: Column}`.
- `app/common/crud.py` — added `filters: Sequence[ColumnElement[bool]] | None = None` to `get_paginated_list`; applied before `count_stmt` so `total` reflects filters.
- `app/common/factories.py` — added `Request` injection to `list_entries`; builds `_filterable` map at factory-construction time; walks `request.query_params.multi_items()` per request; skips reserved params (`skip`, `limit`, `search`); collects unknowns and coercion errors; raises 422 (unknowns listed sorted, coercion reports first failure); builds `col.in_(values)` clauses; passes to `get_paginated_list`.
- `app/schools/tests/test_router.py` — appended `TestListSchoolsColumnFilters` (9 tests: exact match, multi-value OR, AND across columns, unknown 422, multiple unknowns 422, bad type 422, search+filter compose, audit column blocked, filtered total).
- `app/wa_codes/tests/test_router.py` — appended `TestListWACodesColumnFilters` (2 tests: filter by level success case, unknown column 422).
- `app/PATTERNS.md` — added entry **#15 — Factory query-param column filters**.
- `app/common/README.md` — documented `introspection.py` and updated factory section.

All 78 tests in the affected files pass (no regressions).

---

## Non-obvious Decisions

- **`_filterable` built at factory construction, not per-request.** The column map is static — computing it once avoids inspecting the mapper on every GET.
- **`col.in_(values)` always** — even single-value filters use `.in_([v])` rather than `== v`. Keeps the clause-building loop uniform.
- **Unknown columns reported, coercion errors reported separately** — unknowns list all bad names sorted; coercion reports first failure only. Tests confirm both.
- **Audit fields excluded via `AuditMixin.__annotations__`** — self-updating if AuditMixin gains new fields.

---

## Next Step

Phase 1.7 is complete. The known follow-up from the roadmap is:

**Work-auths migration (separate session):** `GET /work-auths/?project_id=` is currently hand-rolled and returns a single object. After Phase 1.7 lands, migrate it onto the factory (breaking FE contract change: single object → paginated list). Needs a `frontend/HANDOFF.md` note before implementing. That is its own session.

After that, the next major phase is **Phase 2 work** or **Phase 6.5**, depending on priority.

Note: Phase 6.5 has an open design question — **placeholder→actual matching layer is NOT FINALIZED** (see roadmap). That must be revisited before any placeholder promotion logic is implemented.
