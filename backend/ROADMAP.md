# FastAPI Project Management Portal — Development Roadmap

## Employees vs. Users: Keep Them Separate

**Keep them separate.** They serve fundamentally different purposes: `users` are auth/permission entities; `employees` are operational/billing entities. Conflating them would pollute both with irrelevant fields and make role semantics ambiguous. To handle overlap (a user who is also an employee), add a nullable `employee_id` FK on `users`. This is clean, optional, and doesn't force the tables to share a schema.

---

## Project Structure

```
app/
├── main.py
├── config.py                  # pydantic-settings, env vars
├── database.py                # engine, SessionLocal, Base
├── dependencies.py            # shared FastAPI deps (get_db, get_current_user)
│
├── auth/
│   ├── router.py              # /login, /refresh, /me
│   ├── schemas.py
│   ├── service.py
│   └── utils.py               # JWT encode/decode, password hashing
│
├── users/
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
│
├── employees/
│   ├── models.py              # Employee, EmployeeRole (time-bound)
│   ├── router.py
│   ├── schemas.py
│   └── service.py
│
├── schools/
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
│
├── contractors/
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
│
├── hygienists/
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
│
├── wa_codes/
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
│
├── work_auths/
│   ├── models.py              # WorkAuth, WA <-> wa_codes link, RFA records
│   ├── router.py
│   ├── schemas.py
│   └── service.py
│
├── deliverables/
│   ├── models.py              # Deliverable def, ProjectDeliverable (status per project)
│   ├── router.py
│   ├── schemas.py
│   └── service.py
│
├── projects/
│   ├── models.py              # Project, ProjectSchoolLink, ProjectContractorLink,
│   │                          # ProjectHygienistLink, ManagerProjectAssignment (audit)
│   ├── router.py
│   ├── schemas.py
│   └── service.py             # project status derivation logic lives here
│
├── time_entries/
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py             # role validation
│
├── lab_results/
│   ├── models.py              # config: SampleType, SampleSubtype, SampleUnitType, TurnaroundOption
│   │                          # data:   SampleBatch, SampleBatchUnit, SampleBatchInspector
│   ├── schemas.py
│   ├── router/
│   │   ├── __init__.py
│   │   ├── config.py          # admin CRUD: sample_types, subtypes, unit_types, turnaround_options
│   │   └── batches.py         # data entry: sample_batches, units, inspectors
│   └── service.py
│
└── common/
    ├── enums.py               # all Enum definitions in one place
        ├── validators.py          # project_num regex, school code regex, etc.
            └── exceptions.py         # custom HTTPExceptions
```

---

## Development Roadmap

### Phase 0 — Foundation

> Do this before writing a single model.

- [x] Create repo, initialize virtualenv, `pyproject.toml` or `requirements.txt`
- [x] Install core deps: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic-settings`, `passlib[bcrypt]`, `python-jose`
- [x] Set up `config.py` with `pydantic-settings` (reads from `.env`: `DATABASE_URL`, `SECRET_KEY`, etc.)
- [x] Set up `database.py` — SQLAlchemy engine, `SessionLocal`, declarative `Base`
- [x] **Initialize Alembic** — fully set up with async support (`render_as_batch=True` for SQLite); 3 migrations in `migrations/versions/`
- [x] Add `GET /health` endpoint in `main.py` to confirm app boots — _implemented as `GET /` returning `{"status": "SCA IH Tracker API is running"}`_
- [x] Set up `common/enums.py` — define all enums now so models can import them cleanly

---

### Phase 1 — Base/Seed Tables

> Each step: write model → write Alembic migration → write Pydantic schemas → write CRUD router → write seed script

- [x] `schools` — model, migration, read endpoints (`GET /schools/`, `GET /schools/{id}`), batch CSV import (`POST /schools/batch/import`)
- [x] `contractors` — model, migration, batch CSV import (`POST /contractors/batch/import`) — _no standalone read endpoints yet_
- [x] `hygienists` — model, migration, full CRUD (`GET/POST/PATCH/DELETE /hygienists/`) — _seed via `data/seed/hygienists.csv` when available_
- [x] `wa_codes` — model, migration, read + search (`GET /wa-codes/`, `GET /wa-codes/{id_or_code}`), batch CSV import (`POST /wa-codes/batch/import`) — _seed via `data/seed/wa_codes.csv`_
- [x] `deliverables` — model, migration, read + search (`GET /deliverables/`), batch CSV import (`POST /deliverables/batch/import`) — _seed via `data/seed/deliverables.csv`_
- [x] `employees` — model + batch CSV import; added read endpoints (`GET /employees/`, `GET /employees/{id}`); `employee_roles` — model, migration, full CRUD (`GET/POST/PATCH/DELETE /employees/{id}/roles`), with application-level date-overlap validation
- [x] `users` + `roles` + `permissions` (RBAC: `role <-> permissions` M2M, `user <-> role` FK) — model + db init script (`app/scripts/db.py`) seeds roles and permissions
- [x] Auth endpoints: `POST /auth/token` (returns JWT), `GET /users/me`
- [x] Wire `get_current_user` dependency, add `PermissionChecker` permission-checking dependency

---

### Phase 1.5 — Thin CRUD Backfill

> Fills gaps in reference-table endpoints deferred during Phase 1 (only list + batch import were built at the time). Each entity is its own session. No new patterns — follow `app/hygienists/router/base.py` as the reference shape.

**Design decision — no generic CRUD factory:** Considered and rejected. Only 2 entities (hygienists, contractors) cleanly fit a `create_basic_crud_router` factory; the rest need per-entity hooks (uniqueness checks, identifier lookups, level immutability) that would widen the factory surface without real leverage. Hand-written routers keep OpenAPI schema names clean for frontend codegen and keep stack traces local to the entity module. Revisit only if a fourth identical thin-CRUD entity appears.

- [x] `contractors` — `GET /contractors/`, `GET /contractors/{id}`, `POST /contractors/`, `PATCH /contractors/{id}` (full thin CRUD; nothing beyond batch import exists today)
- [x] `schools` — `POST /schools/`, `PATCH /schools/{id}` (422 on duplicate `code`; `created_by_id`/`updated_by_id` via `get_current_user`; GET-by-id already covered by the existing identifier route)
- [x] `wa_codes` — `POST /wa-codes/`, `PATCH /wa-codes/{id}`; 422 on duplicate `code` or `description`; PATCH rejects any `level` change unconditionally (no reference check — level is immutable at the API layer, period)
- [x] `employees` (base entity) — `POST /employees/`, `PATCH /employees/{id}`; `display_name` (unique, NOT NULL) added — auto-derived from `"{first_name} {last_name}"` with numeric suffix on collision; `email` promoted to `unique=True`; batch CSV import updated via `custom_validator` to generate `display_name` per row; employee-role CRUD unaffected

---

### Phase 1.6 — Guarded DELETE and Connections Endpoints ✓ COMPLETE

> Fills the missing D in CRUD for all thin reference entities. Done now (between Phase 6 and 6.5 in calendar order) because delete without referential guards is unsafe and the connections endpoint is a prerequisite for the frontend delete-confirmation UX.

**Pattern (see PATTERNS.md #14):**

Each entity gets two new endpoints:

- `GET /{entity_id}/connections` — returns a dict of `{label: count}` for every table that references this entity. Powers the delete-confirmation dialog in the UI.
- `DELETE /{entity_id}` — runs the same reference checks internally; if any count > 0, returns **409** with `{"blocked_by": [...labels...]}` listing *all* blocking reasons at once (not fail-fast). If clear, deletes and returns 204.

Both handlers call a shared `_get_{entity}_references(db, entity_id) -> dict[str, int]` helper defined next to the router. The helper is not a framework utility — it is per-entity because the referencing tables are different for each entity.

**Session A — Infrastructure:** ✓ COMPLETE

- [x] `app/common/guards.py` — `assert_deletable(refs: dict[str, int]) -> None`; raises `HTTPException(409, {"blocked_by": [label for label, count in refs.items() if count > 0]})` if any count is nonzero; no-op otherwise. Thin wrapper so routers stay readable.
- [x] Add PATTERNS.md entry **#14 — Guarded DELETE**: `_get_{entity}_references` helper + `assert_deletable` + TOCTOU note (connections endpoint result is stale by delete time; delete guard re-runs independently).

**Session B — Employees:** ✓ COMPLETE

- [x] `_get_employee_references(db, employee_id)` — checks `time_entries.employee_id`, `sample_batch_inspectors.employee_id`
- [x] `GET /employees/{employee_id}/connections`
- [x] `DELETE /employees/{employee_id}` — guarded; `employee_roles` rows cascade automatically (existing `ondelete=CASCADE`)

**Session C — Schools, Contractors, Hygienists:** ✓ COMPLETE

- [x] `_get_school_references` — checks `project_school_links` (even though it cascades, a school linked to any project should not be silently wiped)
- [x] `GET /schools/{school_id}/connections` + `DELETE /schools/{school_id}`
- [x] `_get_contractor_references` — checks `project_contractors_links`
- [x] `GET /contractors/{contractor_id}/connections` + `DELETE /contractors/{contractor_id}`
- [x] `_get_hygienist_references` — checks `project_hygienist_links`
- [x] `GET /hygienists/{hygienist_id}/connections` + `DELETE /hygienists/{hygienist_id}` (upgraded existing unguarded DELETE)

**Session D — WA Codes and Deliverables:** ✓ COMPLETE

- [x] `_get_wa_code_references` — checks `work_auth_project_codes`, `work_auth_building_codes`, `rfa_project_codes`, `rfa_building_codes`, `deliverable_wa_code_triggers`, `sample_type_wa_codes`
- [x] `GET /wa-codes/{wa_code_id}/connections` + `DELETE /wa-codes/{wa_code_id}`
- [x] `_get_deliverable_references` — checks `project_deliverables`, `project_building_deliverables`, `deliverable_wa_code_triggers`
- [x] `GET /deliverables/{deliverable_id}/connections` + `DELETE /deliverables/{deliverable_id}`

---

### Phase 1.7 — Generic Column Filtering in `create_readonly_router`

> Cross-cutting infrastructure. Extends the factory so every factory-backed list endpoint supports query-param column filters without per-entity boilerplate.

**Filter shape:**

- `GET /[entity]` → paginated list (unchanged)
- `GET /[entity]?col=v` → exact match
- `GET /[entity]?col=v1&col=v2` → `col IN (v1, v2)` (OR within a column via repeated param)
- `GET /[entity]?col_a=v1&col_b=v2` → AND across columns
- Unknown column → 422, all bad names listed in the detail message

**Design decisions:**
- Filterable set: all scalar columns except `AuditMixin` fields (`created_at`, `updated_at`, `created_by_id`, `updated_by_id`)
- Relationship filtering (e.g. `role_type`) is out of scope — column-only
- Column filters and `search=` compose (AND); `search_attr` / `search` are not deprecated
- Column filters do not appear in OpenAPI schema (consumed via `Request`) — acceptable for a dynamic surface

**Work:**

- [x] `app/common/introspection.py` — `filterable_columns(model) -> dict[str, Column]`; audit-field denylist
- [x] `app/common/crud.py` — add `filters: Sequence[ColumnElement[bool]] | None` param to `get_paginated_list`
- [x] `app/common/factories.py` — accept `request: Request`; validate + coerce query params; build `col.in_([...])` clauses; pass filters to `get_paginated_list`
- [x] `app/schools/tests/test_router.py` — `TestListSchoolsColumnFilters` (canonical factory test suite)
- [x] `app/wa_codes/tests/test_router.py` — one cross-entity smoke test
- [x] `app/PATTERNS.md` + `app/common/README.md` — document filter contract

**Follow-up (separate session after this lands):** Migrate `app/work_auths/router/base.py` hand-rolled `GET /` onto the factory; retire the single-object endpoint; add `frontend/HANDOFF.md` note about the breaking shape change (single object → paginated list).

---

### Phase 1.8 — Factor `/connections` + guarded DELETE into shared factory

> Cross-cutting infrastructure. The six entities that implement `GET /{id}/connections` + guarded `DELETE /{id}` today all do so with ~40 lines of hand-rolled, per-entity code (`_get_*_references` helper, untyped dict return, `assert_deletable` call). Every `/connections` endpoint in OpenAPI is typed as `unknown`, blocking the frontend from removing casts. Replace with a `create_guarded_delete_router` factory (alongside `create_readonly_router` in `app/common/factories.py`) that generates a named `*Connections` Pydantic schema per entity via `pydantic.create_model` and emits both endpoints with strict typing.

Full design detail (factory signature, per-entity ref inventory, line numbers for all six modules) is in the plan file:
`C:\Users\msilberstein\.claude\plans\reference-the-2-fe-lucky-sketch.md` (Appendix section).

**Session A — Factory primitive + tests + PATTERNS.md update:** ✓ COMPLETE

- [x] `app/common/factories.py` — `create_guarded_delete_router(*, model, not_found_detail, refs, path_param_name)` factory; `refs` is `list[tuple[FromClause, ColumnElement[int], str]]` (selectable, FK column, label); builds `{Model.__name__}Connections` via `pydantic.create_model`; emits typed `GET /{id}/connections` + `DELETE /{id}` with `assert_deletable` guard. No callers changed yet.
- [x] `app/common/tests/test_guarded_delete_factory.py` — 404/409/204 coverage + OpenAPI schema name check via `contractors` entity.
- [x] `app/PATTERNS.md` section 14 — rewrite to reference `create_guarded_delete_router`; remove hand-rolled example.

**Session B — Migrate six router modules:** ✓ COMPLETE

- [x] `app/contractors/router/base.py` — delete `_get_contractor_references` + both handlers; `include_router(create_guarded_delete_router(...))`
- [x] `app/hygienists/router/base.py` — same
- [x] `app/schools/router/base.py` — same; uses `Table` selectable (`project_school_links.c.school_id`)
- [x] `app/employees/router/base.py` — same; two refs (`time_entries`, `sample_batch_inspectors`)
- [x] `app/deliverables/router/base.py` — same; three refs
- [x] `app/wa_codes/router/base.py` — same; six refs
- [x] Full test suite passes unchanged (532 tests; response shapes preserved — labels verbatim)

**Session C — Docs + cross-side FE handoff:** ✓ COMPLETE

- [x] HANDOFF.md + ROADMAP.md checkmarks
- [x] `frontend/HANDOFF.md` note: regen OpenAPI client — six new `*Connections` schemas now typed; `hasConnections(unknown)` cast in `WaCodeFormDialog.tsx` can be removed

---

### Phase 2 — Projects Core + Relationships ✓ COMPLETE

- [x] `projects` table — model, migrations, full CRUD (`GET/POST/PATCH/DELETE /projects/`) with name search + pagination; `project_number` field with regex validation
- [x] `project_school_links` (M2M association table) — model, migration — _schools linked via `projects.schools` relationship_
- [x] `ProjectContractorLink` table (composite PK `project_id`+`contractor_id`, `is_current` flag, `assigned_at`) — model, migration
- [x] `project_hygienist_links` (FK, one hygienist per project) — model, migration
- [x] `manager_project_assignments` (audit trail: `project_id`, `user_id`, `assigned_at`, `unassigned_at`, `assigned_by`) — model, migration
- [x] `work_auths` table — model, migration, link to `projects`; columns: `wa_num` (str, unique), `service_id` (str, unique), `project_num` (str, unique), `initiation_date` (Date), `project_id` (FK, unique — one WA per project), `is_saved` (bool — WA file saved on office server); full CRUD; 409 on duplicate project
- [x] `work_auth_project_codes` table — model, migration; PK `(work_auth_id, wa_code_id)`; `fee` (Numeric), `status` (`WACodeStatus` enum), `added_at`; full CRUD under `/work-auths/{id}/project-codes`; 422 if code is building-level; 409 on duplicate
- [x] `work_auth_building_codes` table — model, migration; PK `(work_auth_id, wa_code_id, project_id, school_id)`; composite FK `(project_id, school_id)` → `project_school_links`; `budget` (Numeric), `status`, `added_at`; full CRUD under `/work-auths/{id}/building-codes/{wa_code_id}/{school_id}`; 422 if code is project-level or school not linked to project; 409 on duplicate
- [x] `rfas` table — model, migration; columns: `work_auth_id` (FK), `status` (`pending` \| `approved` \| `rejected` \| `withdrawn`), `submitted_at`, `resolved_at` (nullable — required for approved/rejected, optional for withdrawn), `submitted_by_id` (FK → users, nullable), `notes` (nullable); enforce one-pending-per-work-auth at application layer
- [x] `rfa_project_codes` table — model, migration; PK `(rfa_id, wa_code_id)`; columns: `action` (`add` \| `remove`)
- [x] `rfa_building_codes` table — model, migration; PK `(rfa_id, wa_code_id, project_id, school_id)`; composite FK `(project_id, school_id)` → `project_school_links`; columns: `action` (`add` \| `remove`), `budget_adjustment` (Numeric, nullable)
- [x] CRUD endpoints: `POST /work-auths/{id}/rfas`, `GET /work-auths/{id}/rfas` (history), `PATCH /work-auths/{id}/rfas/{rfa_id}` (resolve); resolve applies `budget_adjustment` to `work_auth_building_codes.budget` on approve; rejected/withdrawn reverts codes to `rfa_needed`
- [x] `deliverable_wa_code_triggers` (M2M join table) — PK `(deliverable_id, wa_code_id)`; maps which wa_codes trigger which deliverables; static config seeded via script; managed under `POST/DELETE /deliverables/{id}/triggers`
- [x] `Deliverable.level` column — `WACodeLevel` enum (`project` \| `building`); added to existing model; project-level deliverables produce one row per project, building-level produce one row per linked school
- [x] `project_deliverables` table — PK `(project_id, deliverable_id)`; columns: `internal_status` (`InternalDeliverableStatus`), `sca_status` (`SCADeliverableStatus`), `notes` (nullable), `added_at`; full CRUD under `/projects/{id}/deliverables`
- [x] `project_building_deliverables` table — PK `(project_id, deliverable_id, school_id)`; composite FK `(project_id, school_id)` → `project_school_links`; same status columns as above; full CRUD under `/projects/{id}/building-deliverables`; 422 if school not linked to project; split from project table for clean PK (nullable school_id in PK is illegal in PostgreSQL)

**Design note — deliverable status tracks:**

Each deliverable row carries two independent statuses:

`InternalDeliverableStatus` (5 values): `incomplete` · `blocked` · `in_review` · `in_revision` · `completed` — tracks internal preparation state; `blocked` requires a `notes` explanation

`SCADeliverableStatus` (6 values): `pending_wa` · `pending_rfa` · `outstanding` · `under_review` · `rejected` · `approved` — tracks the SCA-facing submission lifecycle; the first three are derivable from project/WA/code state and are updated by `recalculate_deliverable_sca_status()` in Phase 5; the last three are set manually when interacting with SCA

**Design note — deliverable row lifecycle:**

Rows can be created from multiple trigger sources (WA code added, lab result recorded, manual entry) — all are valid. Once a row exists, its `sca_status` is always maintained by the same `recalculate_deliverable_sca_status(project_id)` service call regardless of how it was created. This handles the "chicken and egg" ordering: a deliverable can be known-needed and tracked before its WA code or even its WA exist, with `sca_status` advancing automatically as each dependency arrives.

---

### Phase 3 — Time Entries ✓ COMPLETE

- [x] `time_entries` model — columns: `start_datetime` (TIMESTAMP), `end_datetime` (TIMESTAMP, nullable), `employee_id`, `employee_role_id` (FK to specific role instance), `project_id` + `school_id` (composite FK → `project_school_links`), `notes` (nullable)
- [x] Service: validate that `employee_role` was active on `start_datetime.date()` at time of insert; validate role belongs to employee
- [x] `POST /time-entries/` with full validation
- [x] `PATCH /time-entries/{id}` — allow updating `start_datetime`/`end_datetime`/`notes` after the fact (manager adds times from daily logs later); re-validates role active on new date if `start_datetime` changes
- [x] `GET /time-entries/` — list with optional filters: `project_id`, `school_id`, `employee_id`
- [x] `GET /time-entries/{id}` — single fetch

---

### Phase 3.5 — Audit Infrastructure ✓ COMPLETE

> Cross-cutting concern applied in one pass. Doing this incrementally risks inconsistent audit data — a null `updated_by_id` would be indistinguishable from "never edited" vs "edited before we wired this in."

**System user sentinel:**

- [x] Seed a reserved `users` row (`id=1`, `username="system"`, no valid password hash) in `app/scripts/db.py`; this user represents automated writes
- [x] Define `SYSTEM_USER_ID: int = 1` constant in `app/common/config.py`; import it wherever service functions write on behalf of the system

**Apply `AuditMixin` to all business entity models** (migration pending — user-managed):

- [x] `wa_codes`, `deliverables` — reference data; need to know who changed a code definition or deliverable template
- [x] `work_auths`, `work_auth_project_codes`, `work_auth_building_codes` — financial/legal records
- [x] `rfas`, `rfa_project_codes`, `rfa_building_codes` — approval workflow
- [x] `projects`, `employees`, `employee_roles` — core operational data
- [x] `project_deliverables`, `project_building_deliverables` — status tracking
- [x] `time_entries`, `sample_batches` — field activity; also carry `source`/`status` (see Phase 4)
- [x] `sample_types` and all config sub-tables — admin-managed, still auditable
- [x] `schools`, `contractors`, `hygienists` — reference data; address/name changes have downstream effects on reports (see Design Note)
- [x] **Exclude**: `manager_project_assignments` (already a purpose-built audit trail); `project_school_links`, `project_contractor_links`, `project_hygienist_links` (managed via parent; parent's audit covers them); `users`, `roles`, `permissions` (auth layer)

**Wire `created_by_id` / `updated_by_id` into all write endpoints** on audited models:

- [x] Add `current_user: User = Depends(get_current_user)` to every create/update route on audited models; set `created_by_id = current_user.id` on insert and `updated_by_id = current_user.id` on update
- [x] For system-initiated writes (quick-add time entry, status recalculation, orphan flagging), pass `user_id=SYSTEM_USER_ID` into the service function explicitly

**Audit tests:**

- [x] `POST /time-entries/` sets `created_by_id`; `PATCH` sets `updated_by_id`
- [x] `POST /lab-results/batches/` sets `created_by_id`; `PATCH` sets `updated_by_id`
- [x] `POST /work-auths` sets `created_by_id`; `PATCH` sets `updated_by_id`
- [x] Batch CSV import (`POST /schools/batch/import`) sets `created_by_id` on created records
- [x] System user sentinel: `"!"` hash blocks all `verify_password` attempts

---

### Phase 3.6 — Notes and Blockers ✓ COMPLETE

> Prerequisite for Phase 6: project closure gates on unresolved blocking notes across all project entities.
> Phase 4 no longer requires Phase 3.6 — overlap detection was changed to return 422 at entry time rather than creating system notes (see Phase 4 design decisions).

**Session breakdown** (one building step per session):

- **Session A — Data model + migration:** `app/notes/` module scaffold; `Note` model; `NoteEntityType` + `NoteType` enums in `app/common/enums.py`; Pydantic schemas (no endpoints yet); module README. Stop for user-generated migration. ✓ COMPLETE
- **Session B — Service layer:** `create_system_note()`, `auto_resolve_system_notes()`, `get_blocking_notes_for_project()` with unit tests. ✓ COMPLETE
- **Session C — Endpoints:** `GET/POST /notes/{entity_type}/{entity_id}`, `POST /notes/{id}/reply`, `PATCH /notes/{id}/resolve`, `GET /projects/{id}/blocking-issues` + API tests. ✓ COMPLETE
- **Session D — Integration:** wire `create_system_note` into any service paths that should emit system notes (e.g. deliverable blocking-note gate on status transitions); update relevant module READMEs. ✓ COMPLETE

**Data model:** ✓ Session A complete

**Service layer:** ✓ Session B complete

- [x] `notes` table — `entity_type` (enum: `project` \| `time_entry` \| `deliverable` \| `sample_batch`), `entity_id` (int; no DB-level FK — polymorphic attachment, app-layer enforced), `parent_note_id` (nullable FK → `notes.id`, `ondelete=CASCADE`; one level of replies only), `body` (text), `note_type` (nullable enum: `time_entry_conflict` \| future system types; `NULL` for user-authored notes), `is_blocking` (bool), `is_resolved` (bool, default `False`), `resolved_by_id` (nullable FK → `users.id`), `resolved_at` (nullable timestamp); composite index on `(entity_type, entity_id)`; `AuditMixin` covers `created_at`, `updated_at`, `created_by_id`, `updated_by_id` (`created_by_id = SYSTEM_USER_ID` for system notes). _Note: `work_auth` intentionally omitted from `NoteEntityType` — not needed for closure gating and can be added later if a use case emerges._
- [x] `NoteEntityType` + `NoteType` enums in `app/common/enums.py`
- [x] Pydantic schemas in `app/notes/schemas.py`: `NoteCreate`, `NoteReply`, `NoteResolve`, `NoteRead` (with nested `replies`)

**Service layer:**

- [x] `create_system_note(entity_type, entity_id, note_type, body, db)` — inserts a blocking note with `created_by_id = SYSTEM_USER_ID`; de-duplicated on `(entity_type, entity_id, note_type)` for unresolved notes
- [x] `auto_resolve_system_notes(entity_type, entity_id, note_type, db)` — marks all unresolved notes of a given type on a given entity as resolved (`resolved_by_id = SYSTEM_USER_ID`, `resolved_at = now()`); signature includes `entity_type` (roadmap omitted it — required to avoid resolving notes on the wrong entity type when entity IDs collide across tables)
- [x] `get_blocking_notes_for_project(project_id, db)` — **lives in `app/projects/services.py`** (not `app/notes/service.py`). Aggregates all unresolved blocking notes across the project, its time entries, deliverables, and sample batches; returns `list[BlockingIssue]` (schema in `app/notes/schemas.py`). Deliverable notes attach to the `deliverable_id` (template ID); batches with `time_entry_id=NULL` are excluded (no project association).

**Endpoints:**

- [x] `GET /notes/{entity_type}/{entity_id}` — all notes on this entity, threaded (top-level notes with their replies nested); ordered by `created_at`
- [x] `POST /notes/{entity_type}/{entity_id}` — create a user note; request body includes `is_blocking` (bool) and `body` (text); validates entity exists before inserting
- [x] `POST /notes/{note_id}/reply` — add a reply to a top-level note; replies are never blocking
- [x] `PATCH /notes/{note_id}/resolve` — mark a user-authored blocking note as resolved; requires a `resolution_note` field in the request body (auto-appended as a reply to preserve the resolution rationale); system notes (`note_type IS NOT NULL`) cannot be manually resolved — they auto-resolve when the condition clears
- [x] `GET /projects/{id}/blocking-issues` — aggregated unresolved blocking notes across all entities belonging to the project; used by the project status engine and by `lock_project_records()`

**Integration rules:**

- `entity_type + entity_id` is a polymorphic reference — no DB-level FK; service validates entity existence before creating a note
- [x] Blocking notes on a deliverable block status transitions to `in_review` (internal) or `under_review`/`approved` (SCA) — checked in both deliverable PATCH endpoints (`update_project_deliverable`, `update_building_deliverable`) in `app/projects/router/deliverables.py`
- Future `@mention` support: do not sanitize or strip `@username` patterns from note bodies; the body is stored as-is so a future mention parser can extract them without a data migration (see Follow-up Project — User Notifications)

---

### Phase 4 — Lab Results ✓ COMPLETE (migration pending — user-managed)

Two-layer design: admin-configurable type definitions (config layer) + per-job recorded data (data layer). Adding a new sample type requires no code or migration — an admin adds rows to the config tables.

**Config layer** (admin-managed, seeded initially, rarely change): ✓ COMPLETE

- [x] `sample_types` — `id`, `name` ("PCM", "Bulk", "LDW"), `description`, `allows_multiple_inspectors` (bool)
- [x] `sample_subtypes` — `id`, `sample_type_id` (FK), `name` ("Pre-Abatement", "During", "Final", "Ambient")
- [x] `sample_unit_types` — `id`, `sample_type_id` (FK), `name` ("PLM", "NOB-PLM", "NOB-TEM", "NOB-PREP", "PCM"); unit types are scoped to a sample type — a bulk batch cannot contain PCM units
- [x] `turnaround_options` — `id`, `sample_type_id` (FK), `hours` (int), `label` ("1hr Rush", "6hr", "24hr Standard")
- [x] `sample_type_required_roles` — M2M: `sample_type_id`, `role_type` (enum); which employee role types may collect this sample
- [x] `sample_type_wa_codes` — M2M: `sample_type_id`, `wa_code_id` (FK); which WA codes are required to bill this sample type
- [x] Admin CRUD under `/lab-results/config/sample-types`; seed initial PCM + Bulk definitions on first deploy

**Data layer** (recorded per job): ✓ COMPLETE (basic CRUD — state model pending)

- [x] `sample_batches` — `id`, `sample_type_id`, `sample_subtype_id` (nullable), `turnaround_option_id` (nullable), `time_entry_id` (FK, currently required — make nullable in next migration), `batch_num`, `is_report`, `date_collected`, `notes`
- [x] `sample_batch_units` — `id`, `batch_id` (FK), `sample_unit_type_id` (FK), `quantity` (int), `unit_rate` (Numeric, nullable)
- [x] `sample_batch_inspectors` — M2M: `batch_id`, `employee_id` (FK)
- [x] App-layer validation on batch create: unit type must belong to the batch's sample type (422 otherwise); employee must hold a role in `sample_type_required_roles` for the type
- [x] CRUD endpoints: `POST/GET /lab-results/batches/`, `GET /lab-results/batches/{id}`, `PATCH /lab-results/batches/{id}`, `DELETE /lab-results/batches/{id}`

**Time entry state model** — **NEXT STEP** (one migration adds `status` to `time_entries`):

> **Design decision — `source` column dropped:** `created_by_id == SYSTEM_USER_ID` already encodes whether an entry was system-created — a redundant column adds a migration with no new information.
>
> **Design decision — overlap returns 422 at entry time (changed from system notes):** If a POST or PATCH time entry would overlap an existing entry for the same employee (checked cross-project), the request returns 422 identifying the conflicting entry ID. No conflicting entry is created. This was changed from the earlier design (create both + system notes) because the team is small and internal — the practical case is a manager correcting a data-entry error, not two managers racing to record real parallel work.
>
> **Design decision — `orphaned` status dropped:** Time entries are rarely deleted in practice. Rather than detect and mark batches orphaned when their entry's date range changes, block deletion of any time entry that has `active` or `discarded` batches (409 with explanation). Managers must reassign or delete batches first.

- [x] `time_entries.status` — `assumed` \| `entered` \| `locked`; default `entered` for manager-created entries
- [x] When a manager edits a `status=assumed` entry, set `status → entered`; `created_by_id` stays as `SYSTEM_USER_ID`; `updated_by_id` = manager's user ID
- [x] Overlap detection at insert/update: 422 if the new/updated entry would overlap any existing entry for that employee (cross-project); NULL `end_datetime` treated as full day (midnight to midnight) since assumed entries always start at `00:00:00`
- [x] `sample_batches.status` — `active` \| `discarded` \| `locked`; default `active`
- [x] Make `sample_batches.time_entry_id` nullable; batch with no time entry is a blocking issue (dismissable requirements design deferred to after Phase 6)
- [x] Block deletion of `time_entries` that have `active` or `discarded` batches (409)
- [x] `POST /lab-results/batches/{id}/discard` — dedicated discard endpoint (not a PATCH field); sets `status=discarded`; 422 if already discarded or locked

**Quick-add endpoint** (manager-facing; no pre-existing time entry required):

- [x] `POST /lab-results/batches/quick-add` — accepts `employee_id`, `employee_role_id`, `project_id`, `school_id`, `date_on_site` plus all batch fields; creates assumed `TimeEntry` (midnight of `date_on_site`, `end=NULL`, `created_by_id=SYSTEM_USER_ID`) and `SampleBatch` atomically; all validations run before any write; overlap check runs against the full-day span

**Deferred — Dismissable requirements** (discovered during Phase 4 planning):

- [ ] A batch with `time_entry_id=NULL` should be surfaceable as a blocking issue that a manager can explicitly dismiss (acknowledging the problem and excluding those samples from billing). Needs design: storage, permissions, billing integration. `time_entry_id` nullable (Phase 4) is the prerequisite. Implement after Phase 6.

**Billing runway** (not implemented yet — see Follow-up Project):

- [ ] `sample_rates` — `id`, `contract_id` (FK → contracts, **nullable** — null means global/default rate), `sample_unit_type_id` (FK), `turnaround_option_id` (FK), `rate` (Numeric), `effective_from` (Date); add this table now so the FK shape is locked in before contracts arrive; rate lookup: prefer contract-specific row, fall back to `contract_id IS NULL`; when a batch is recorded, resolve the applicable rate and store it on `sample_batch_units.unit_rate`

---

### Phase 5 — Observability _(deferred — build after Phase 6)_

> **Design decision:** Deferred until the app is in production with real data. This is a small internal tool with a small team; premature observability work delays Phase 6 which is the actual product value. SQLite in dev doesn't reflect production query characteristics anyway. Revisit once deployed.

**Goal:** make slow queries and N+1 regressions visible in development and in production before they become user-facing problems.

- [ ] **SQL logging middleware** — read `LOG_SQL` env var at startup; if set, attach a SQLAlchemy `before_cursor_execute` event listener that logs every statement + elapsed time to the `sqlalchemy.engine` logger; default off in production, on-demand in dev
- [ ] **Slow request middleware** — FastAPI `@app.middleware("http")` that records wall time per request; logs a `WARNING` if duration exceeds a configurable threshold (start at 500ms); include route path and method in the log line so slow endpoints are immediately identifiable
- [ ] **Per-request query counter** — extend the event listener to increment a counter stored in a context variable; log query count alongside duration on slow requests; a single request firing >20 queries is a red flag worth investigating
- [ ] **Test-layer query count assertions** — add a `query_counter` pytest fixture (wraps the same event listener) that exposes `.count` after a test block; use it on key list endpoints to assert `query_count <= N` and catch N+1 regressions before they ship; apply to the most join-heavy endpoints first (project status, batch list with units)
- [ ] **Dev command** — `just api log=true` passes `LOG_SQL=true` to uvicorn; no separate recipe needed (see justfile)

---

### Phase 6 — Project Status Engine

> No new models. All four services land in `app/projects/services.py` alongside the existing `get_blocking_notes_for_project()` from Phase 3.6. The `GET /projects/{id}/blocking-issues` endpoint is already live from Phase 3.6 — Phase 6 consumes it, does not re-create it.

**Session breakdown** (one building step per session):

- **Session A — Deliverable derivation services:** `recalculate_deliverable_sca_status(project_id)` and `ensure_deliverables_exist(project_id)` as pure service functions in `app/projects/services.py`, with unit tests. No endpoint wiring in this session.
- **Session B — Integration: wire derivation into mutation paths:** call `recalculate_deliverable_sca_status` from work-auth, WA-code, and RFA-resolve endpoints; call `ensure_deliverables_exist` from time-entry and batch creation; emit the sample-type WA-code gap flag as a blocking system note when a batch is recorded.
- **Session C — Project status read-side:** `derive_project_status(project_id)` pure function + `ProjectStatusRead` schema + `GET /projects/{id}/status` endpoint (reuses the Phase 3.6 blocking-issues aggregator).
- **Session D — Project closure and record locking:** `lock_project_records(project_id)` service (blocking-note gate + cascade to `time_entries`/`sample_batches`), `POST /projects/{id}/close` endpoint, and `status != locked` guards on time-entry and batch mutation endpoints.

**Session A — Deliverable derivation services:**

- [x] `recalculate_deliverable_sca_status(project_id, db)` — updates `sca_status` on all `project_deliverables` and `project_building_deliverables` rows where status is still derivable (`pending_wa`, `pending_rfa`, `outstanding`); never overwrites manual terminal states (`under_review` / `rejected` / `approved`)
- [x] `ensure_deliverables_exist(project_id, db)` — checks `deliverable_wa_code_triggers` and inserts any missing deliverable rows; respects `Deliverable.level` (project vs. building); idempotent so it is safe to call on every mutation path
- [x] Unit tests in `app/projects/tests/test_projects_service.py`: status promotion across `pending_wa → pending_rfa → outstanding`; manual statuses untouched; `ensure_deliverables_exist` idempotency and level-aware row creation

**Session B — Integration: wire derivation into mutation paths:** ✓ COMPLETE

- [x] Call `recalculate_deliverable_sca_status()` from: `POST /work-auths/`, `POST/DELETE /work-auths/{id}/project-codes`, `POST/DELETE /work-auths/{id}/building-codes`, `PATCH /work-auths/{id}/rfas/{rfa_id}` (on resolve — approved / rejected / withdrawn)
- [x] Call `ensure_deliverables_exist()` from all of the above WA paths plus: `POST /time-entries/`, `POST /lab-results/batches/`, `POST /lab-results/batches/quick-add` — so deliverables are tracked as soon as work is recorded, before the WA exists; also called from WA paths so newly triggered rows are created and immediately recalculated in one shot
- [x] **Sample-type WA-code gap flag:** `check_sample_type_gap_note(project_id, db)` in `app/projects/services.py`; `NoteType.MISSING_SAMPLE_TYPE_WA_CODE` added to enums; called from batch-creation paths (emit note) and WA code-add paths (auto-resolve if gap is filled)
- [x] Integration tests: WA code added → deliverables exist with correct `sca_status`; RFA approved → statuses advance; RFA rejected → status unchanged; batch with missing sample-type WA code → blocking note; add the missing code → note auto-resolves

**Session C — Project status read-side:** ✓ COMPLETE

- [x] `derive_project_status(project_id, db)` — pure function inspecting deliverable statuses, pending RFAs, unconfirmed time entries, and unresolved blocking notes via `get_blocking_notes_for_project()`; returns `ProjectStatusRead`; no writes
- [x] `ProjectStatusRead` schema in `app/projects/schemas.py` — `status`, `has_work_auth`, `pending_rfa_count`, `outstanding_deliverable_count`, `unconfirmed_time_entry_count`, `blocking_issues`
- [x] `GET /projects/{id}/status` endpoint in `app/projects/router/base.py`
- [x] Tests: 8 service tests (`TestDeriveProjectStatus`) + 2 endpoint tests

**Design note — `ProjectStatus.SETUP`:** Defined as "no time entries recorded yet" (no work has started), not "no WA issued." A project can have a WA but be in `SETUP` if no field work has been recorded. `BLOCKED` overrides all other states including `SETUP`.

**Session D — Project closure and record locking:** ✓ COMPLETE

- [x] `lock_project_records(project_id, db, user_id)` — raises 409 with `blocking_issues` payload if any unresolved blocking notes exist; transitions `time_entries` (`assumed`/`entered` → `locked`) and `active` `sample_batches` → `locked`; sets `Project.is_locked = True`
- [x] `POST /projects/{id}/close` endpoint — 409 with `blocking_issues` payload on refusal, 200 + `ProjectStatusRead` (status=LOCKED) on success; 409 if already closed
- [x] `status != locked` guards on PATCH/DELETE for `time_entries` and PATCH/DELETE for `sample_batches` (422)
- [x] `Project.is_locked: bool` column added (migration needed — user-managed); `derive_project_status` short-circuits to `LOCKED` when set
- [x] 11 tests in `app/projects/tests/test_project_closure.py`

**Design note — assumed entries at closure:** `lock_project_records` currently locks assumed entries without blocking. `unconfirmed_time_entry_count > 0` is already surfaced in `ProjectStatusRead`; whether to make it a hard closure gate is deferred (see memory).

---

### Phase 6.5 — `ProjectRequirement` Protocol + Closure-Gating Silos

Three new closure-gating silos (`project_document_requirements`, `contractor_payment_records`, `project_dep_filings`) ship as native implementors of a generic `ProjectRequirement` protocol introduced in this phase. The closure-gate aggregator walks one registry instead of four bespoke note sources.

Full design eval: `PLANNING.md`. Concrete plan reference (working doc): `~/.claude/plans/i-want-to-finish-abundant-bunny.md`.

**Why the protocol now (not after the silos ship):** today's closure gate walks four bespoke note sources plus `is_locked`; adding three more silos as standalone tables means three more bespoke walks and three parallel "saved on file? / dismissed? / fulfilled?" patterns. Phase 6.5 is the cheapest moment to introduce the primitive — silos are born native to the protocol instead of being retrofitted later.

**Locked design decisions** (supersede prior Phase 6.5 prose; full reasoning in `PLANNING.md` §6):

1. **Notes module stays orthogonal to requirements.** Notes = "something is wrong"; requirements = "what should be true". Closure aggregator consumes both independently.
2. **Required documents inside a deliverable are fulfilled-by-parent only** — not separately addressable in closure UI.
3. **Dismissibility (`dismissal_reason`, `dismissed_by_id`, `dismissed_at`) lives on the requirement base** as a shared mixin.
4. **Manual-terminal immunity is per-type**, not on the base. Not all requirement types have manual terminals.
5. **Requirement tables carry `AuditMixin`** (per CLAUDE.md §1.2).
6. **De-materialization on triggering WA-code removal: conditional.** Persist if the requirement has progressed past initial state (e.g. CPR with `rfa_submitted_at` set, document with `is_saved=True`); auto-remove if pristine. Mirrors `recalculate_deliverable_sca_status` skip-manual-terminals rule.
7. **Trigger registration is developer-defined throughout.** Both materialization triggers and recalc fan-out are per-type code registrations; admin-managed triggers are over-flexibility.
8. **No polymorphic parent table.** Each requirement type stays in its own table; the protocol is enforced at the Python layer. Avoids JTI/STI tradeoff per PATTERNS.md §4.
9. **File upload infrastructure stays deferred.** `is_saved=True` + `file_id IS NULL` remains a valid permanent state. Each silo gets a nullable `file_id` column ready to wire later.
10. **`wa_code_requirement_triggers` (new admin config) covers the three new silos; existing `deliverable_wa_code_triggers` is unchanged.** Deliverables join the registry via a read-only adapter; Stage 3 (unify trigger tables, fold deliverables natively) is deferred until growth justifies.
11. **`WACodeRequirementTrigger` model lives in `app/project_requirements/`, not `app/wa_codes/`.** The table is load-bearing for both directions: forward (WA code added → materialize requirements) and reverse (requirement fulfilled → infer which WA code to add). Putting the model in `wa_codes` would create a circular dependency once the reverse flow is implemented. The `wa_codes` module never imports from `project_requirements`.
12. **Reverse inference flow (deferred — not Session B).** When a requirement of a given type is saved/fulfilled on a project, the system queries `wa_code_requirement_triggers` for WA codes that include that requirement type, then adds the one with the lexicographically smallest `code` to the project (status: `PENDING_WA`). Adding that WA code then fires `WA_CODE_ADDED`, cascading its other triggers. A new `RequirementEvent` value is needed for the triggering condition (e.g. `REQUIRED_DOCUMENT_SAVED`). The handler lives in `project_requirements` and calls into `work_auths` for the WA code addition — an accepted cross-domain call at the service layer.

**Architecture:**

- New `app/requirements/` module — `ProjectRequirement` protocol, `DismissibleMixin`, optional `ManualTerminalMixin`, `RequirementTypeRegistry`, aggregator, dispatch entry point, read-only adapter for existing deliverables
- New `app/required_docs/` module — three silos as native protocol implementors
- New `wa_code_requirement_triggers` admin config table (extends today's `deliverable_wa_code_triggers` pattern; replaces the earlier `wa_code_expected_entities` proposal)
- `get_unfulfilled_requirements_for_project()` walks the registry; existing `get_blocking_notes_for_project()` (Phase 3.6) stays untouched and is consumed alongside

**Silo behaviour:**

**Silo 1 — `project_document_requirements`** (generic on/off checklist)
- Covers `DAILY_LOG`, `REOCCUPANCY_LETTER`, `MINOR_LETTER`
- Columns: `project_id`, `document_type` (enum), `is_required`, `is_saved`, nullable `employee_id` / `date` / `school_id` / `file_id`, `is_placeholder`, `expected_role_type` (enum, nullable), `notes` + dismissal fields (from `DismissibleMixin`) + `AuditMixin`
- `compute_is_fulfilled() -> is_saved`
- Materialization: `TIME_ENTRY_CREATED` event auto-creates `DAILY_LOG` row when employee role's `requires_daily_log=True`; manual POST for re-occupancy / minor letters
- `try_match()` matches an actual document upload by `(project_id, document_type, employee_id, date, school_id)` tuple equality

**Silo 2 — `contractor_payment_records`** (CPR with RFA+RFP sub-flow)
- One row per `(project, contractor)`. Columns: `project_id`, `contractor_id`, `is_required`, RFA dates/statuses (`rfa_submitted_at`, `rfa_internal_status`+`rfa_internal_resolved_at`, `rfa_sca_status`+`rfa_sca_resolved_at`), RFP dates/statuses through saving (`rfp_submitted_at`, `rfp_internal_status`+`rfp_internal_resolved_at`, `rfp_saved_at`), nullable `file_id`, `notes` + dismissal fields + `AuditMixin`
- Uses `ManualTerminalMixin` for the four sub-states; `compute_is_fulfilled() -> rfp_saved_at IS NOT NULL`. SCA's post-save RFP review intentionally not tracked
- Materialization: `CONTRACTOR_LINKED` event auto-creates one row per `(project, contractor)` with `is_required=True`
- De-materialization on contractor unlink: persist if `rfa_submitted_at IS NOT NULL`; auto-remove if pristine (Decision #6)
- **History via system notes, not a history table.** Re-submitting an RFA/RFP after prior dates were recorded calls `create_system_note()` (Phase 3.6) capturing the prior dates before clearing them. Stage regressions (approved → rejected) likewise get auto-notes

**Silo 3 — `dep_filing_forms` + `project_dep_filings`**
- Admin-managed `dep_filing_forms` (code, label, `is_default_selected`, `display_order`) — adding a new form requires no migration
- `project_dep_filings` — one row per `(project, form)` with `is_saved`, `saved_at`, nullable `file_id`, dismissal fields, `AuditMixin`; unique on `(project_id, dep_filing_form_id)`
- `compute_is_fulfilled() -> is_saved`
- Materialization: manager UX flow ("project has DEP filings" button → form list with common ones pre-checked → POST `{form_ids: [...]}`); no WA-code-driven auto-create

**Cross-cutting:**

- `time_entries.status` gains a fourth value `EXPECTED` (nullable employee/dates; does not participate in overlap checks) — implementation pending in this phase
- Role-type schema: add `requires_daily_log: bool` to role type config. Air techs and project monitors get True; asbestos investigators get False. Admin-toggleable.

**Sessions** (each scoped for context focus; resume from `HANDOFF.md`):

- [x] **Session A — Protocol primitive & deliverable adapter** (Stage 1; no migrations) ✓ COMPLETE
  - `app/project_requirements/protocol.py` — `ProjectRequirement` protocol (runtime-checkable), `DismissibleMixin`, `ManualTerminalMixin`
  - `app/project_requirements/registry.py` — `RequirementTypeRegistry`, `register_requirement_type` decorator; `RequirementEvent` in `app/common/enums.py`
  - `app/project_requirements/aggregator.py` — `get_unfulfilled_requirements_for_project()`
  - `app/project_requirements/adapters/deliverables.py` — `DeliverableRequirementAdapter`, `BuildingDeliverableRequirementAdapter` (read-only; no schema change)
  - `app/project_requirements/tests/` — 29 tests: protocol contract, registry, mixin smoke, aggregator per-row predicate (parametrized × 6 statuses × 2 levels), equivalence gate
  - `app/project_requirements/README.md`
  - **Gate passed:** 29 new + 532 existing tests green; `get_unfulfilled_requirements_for_project()` count == `derive_project_status().outstanding_deliverable_count` on mixed-status fixture.

- [x] **Session B — `wa_code_requirement_triggers` admin config + dispatch entry point** ✓ COMPLETE
  - `wa_code_requirement_triggers` table (`wa_code_id`, `requirement_type_name`, `template_params` JSON, `AuditMixin`); unique on `(wa_code_id, requirement_type_name, template_params_hash)`; model in `app/project_requirements/models.py` (Decision #11)
  - Admin CRUD at `/requirement-triggers/` (flat collection; `wa_code_id` in POST body, query param on GET); validation against the registry (rejects unknown `requirement_type_name`)
  - `app/project_requirements/services.py` — `dispatch_requirement_event(project_id, event, payload, db)` — looks up registered handlers, calls each; forward dispatch only (reverse inference deferred — Decision #12)
  - `app/project_requirements/registry.py` extended — `register_requirement_type(name, events=[...])` declares per-handler event subscriptions; `handlers_for_event(event)` queries them
  - User-managed migration for the new table

- [x] **Session C — Silo 1: `project_document_requirements`** ✓ COMPLETE
  - `app/required_docs/` module (models, schemas, service, router, tests, README)
  - `DocumentType` enum added to `app/common/enums.py` (`DAILY_LOG`, `REOCCUPANCY_LETTER`, `MINOR_LETTER`)
  - `ROLES_REQUIRING_DAILY_LOG` silo-owned mapping in `service.py` (no admin CRUD — pure code)
  - Materializers: `TIME_ENTRY_CREATED`, `WA_CODE_ADDED`, `WA_CODE_REMOVED` (Decision #6 conditional delete)
  - Partial unique index prevents duplicate active rows; dismissed rows allow re-materialization
  - `ProjectDocumentHandler` in `service.py` registered in requirement registry (separate from ORM model to avoid circular import)
  - Dispatch wired in `app/time_entries/router.py` and `app/lab_results/service.py`
  - 50 new tests (643 total, all passing)
  - User-managed migration (pending)

- [ ] **Session D — Silo 2: `contractor_payment_records`**
  - Model + schema + router + service for CPR; `ManualTerminalMixin` applied
  - Add `CPRStageStatus` enum to `app/common/enums.py`
  - Materialization on `CONTRACTOR_LINKED`; de-materialization on contractor unlink (Decision #6)
  - History note integration via `create_system_note()` on RFA/RFP re-submission
  - Per-silo dismissal endpoint
  - User-managed migration

- [ ] **Session E — Silo 3: `dep_filing_forms` + `project_dep_filings`**
  - Admin-managed `dep_filing_forms` config table + CRUD (use `create_readonly_router` + `create_guarded_delete_router` factories)
  - `project_dep_filings` model + schema + router + service
  - Manager UX endpoint: POST `{form_ids: [...]}` materializes rows
  - Per-silo dismissal endpoint
  - User-managed migration

- [ ] **Session F — Closure-gate integration + project status surface**
  - Extend `lock_project_records()` (`app/projects/services.py:509`) to refuse close on any unfulfilled non-dismissed requirement, in addition to the existing blocking-notes check
  - Extend `derive_project_status()` and `ProjectStatusRead` (`app/projects/schemas.py`) — add `unfulfilled_requirement_count`
  - New `GET /projects/{id}/requirements` endpoint
  - `frontend/HANDOFF.md` note: regen OpenAPI client (new `UnfulfilledRequirement`, `ContractorPaymentRecord`, `ProjectDocumentRequirement`, `ProjectDepFiling`, `WaCodeRequirementTrigger`, `DepFilingForm` schemas)
  - ROADMAP.md checkboxes; HANDOFF.md update
  - Final sweep: `python -m pytest tests/ -v` clean

**Deferred out of Phase 6.5 (Stages 3 + 4 and beyond):**

- Migrating `project_deliverables` / `project_building_deliverables` natively into the registry — adapter only for now (Stage 3)
- Admin self-serve config for new requirement *types* (Stage 4)
- File upload infrastructure (polymorphic `files` table, upload endpoints, storage backend) — `file_id` columns are added as nullable per silo
- Project templates proper (`project_templates`, `project_template_wa_codes`)
- Full placeholder sample batches (Phase 4's `time_entry_id=null` + dismiss already covers the lived case)
- Zipped project-package export (one folder per silo)
- Reminder/nudge logic ("CPR stuck at internal review N days") — trivial to layer on once dates exist

---

### Phase 7 — Dashboard Query Endpoints

- [ ] `GET /projects/dashboard/my-outstanding-deliverables`
- [ ] `GET /projects/dashboard/needs-rfa`
- [ ] `GET /projects/dashboard/rfa-pending`
- [ ] `GET /projects/dashboard/ready-to-bill`
- [ ] `GET /projects/dashboard/awaiting-contractor-doc`
- [ ] Add composite DB indexes to support these queries (see Hazards section)

---

## Documentation Plan

### Why this exists

The most common reason documentation goes stale is that it lives somewhere separate from the code. A doc written once and never touched again becomes actively misleading — worse than no doc at all. The strategy here keeps documentation physically close to what it describes and uses formats that are cheap to update alongside code changes.

### What goes where

| Location | Purpose | What NOT to put here |
|---|---|---|
| `backend/ROADMAP.md` | Design intent, decisions made, what's coming next | Implementation details already in code |
| `backend/HANDOFF.md` | Per-session continuity notes; non-obvious technical context | Long-term design (that belongs in roadmap) |
| `backend/app/PATTERNS.md` | Cross-cutting SQLAlchemy/FastAPI patterns that apply to multiple modules | Module-specific behavior |
| `backend/app/{module}/README.md` | Module purpose, non-obvious behavior, what to check before modifying | Things the code already says clearly |
| Inline code comments | The "why" behind non-obvious logic; not what the code does | Obvious or self-documenting operations |

### What each module README covers

Three sections, no more:

1. **Purpose** — one paragraph: what this module owns, and explicitly what it does NOT own (boundary statements prevent scope creep in both code and understanding)
2. **Non-obvious behavior** — anything that will cause a bug if forgotten; technical patterns that aren't visible from reading the surface of the code (e.g., `populate_existing=True`, FK validation in early-return paths)
3. **Before you modify** — specific guard rails for this module; what to test, what service functions to check, what other modules are affected by changes here

### Diagrams (Mermaid)

Mermaid diagrams are embedded as code blocks in Markdown files and render natively in VS Code and GitHub. They're version-controlled text — updating them is editing a file, not screenshotting a whiteboard.

**Use state diagrams for any entity with a status column:**
- `time_entries.status` — `assumed → entered → locked` with transition conditions
- `sample_batches.status` — `active → discarded/locked`
- `notes.is_resolved` — blocking note lifecycle (created → auto-resolved / manually resolved)
- Deliverable `internal_status` and `sca_status` — the two parallel tracks

**Use flowcharts for any validation chain with branching:**
- Batch creation validation (time entry check → role check → subtype → unit types → TAT → inspector count)
- Quick-add time entry resolution (`resolve_or_create_time_entry`)
- Deliverable SCA status recalculation (`recalculate_deliverable_sca_status`)

**Use sequence diagrams for cross-module flows:**
- `POST /lab-results/batches/quick-add` — which service functions are called, in which order, across which modules
- Project closure (`lock_project_records`) — what is checked and in what sequence before locking proceeds

### When to write docs

Write module READMEs **before** writing Phase 4 code — not after. Documentation written before implementation forces you to articulate the design, which catches ambiguities before they become bugs. Documentation written after implementation is usually skipped because the code "already explains it."

Rule of thumb: if you had to stop and think about how something works before writing the code, document it. If it was straightforward, skip it.

### Files to generate (not yet created)

- [ ] `backend/README.md` — module index, how to run dev server, how to run tests, where design docs live
- [ ] `backend/app/PATTERNS.md` — `db.get()` vs `select() + populate_existing`, FK validation in early-return paths, `PermissionChecker` pattern, AuditMixin wiring, rollback test pattern
- [x] `backend/app/lab_results/README.md` — config vs. data layer, batch validation chain flowchart, `populate_existing` warning, state model
- [x] `backend/app/time_entries/README.md` — state diagram, overlap detection + notes integration, quick-add service flow
- [ ] `backend/app/notes/README.md` — polymorphic attachment pattern, system vs. user notes, auto-resolve lifecycle, future @mention hook
- [x] `backend/app/projects/README.md` — status derivation, link table relationships, blocking issues aggregation
- [x] `backend/app/work_auths/README.md` — WA/RFA state machine diagram
- [x] `backend/app/common/README.md` — what lives here, enums policy, AuditMixin overview, factory router pattern

**Additional READMEs created (Phase 0/1 modules with non-obvious behavior):**
- [x] `backend/app/employees/README.md` — time-bound EmployeeRole, overlap validation, nullable user link
- [x] `backend/app/users/README.md` — PermissionChecker pattern, SYSTEM_USER_ID, RBAC structure
- [x] `backend/app/wa_codes/README.md` — WACodeLevel downstream effects, immutability once in use
- [x] `backend/app/deliverables/README.md` — dual status tracks, trigger config, separate project/building tables

Generate these after Phase 3.6 is implemented, before Phase 4 code is written.

---

## Analysis + Hazards

### Hazard 1 — Billing rate split across midnight / rate boundaries _(deferred — see Follow-up Project)_

Rate-split calculation is deferred to the billing follow-up project. Time entries store `start_datetime` / `end_datetime` as timestamps, which makes the span math straightforward when billing is eventually implemented.

**When billing is built**, the function lives in `employees/service.py`:

```python
def calculate_billable_segments(employee_id, role_type, start_dt, end_dt) -> list[BillingSegment]
```

A shift can cross a calendar day (detect when `end_datetime.date() > start_datetime.date()`) or a rate-change boundary (start of a new `employee_role` record). The function should return a list of `(hours, rate)` segments and be tested exhaustively before being connected to the API.

---

### Hazard 2 — Employee role overlap constraint _(must have DB-level enforcement)_

"No two roles of the same type can overlap for the same employee" cannot be enforced safely at the application layer alone due to race conditions.

**If using PostgreSQL**, use an exclusion constraint with `daterange`:

```sql
EXCLUDE USING gist (
    employee_id WITH =,
        role_type WITH =,
            daterange(start_date, end_date, '[)') WITH &&
            )
```

This requires the `btree_gist` extension. Add it in an Alembic migration. Without this, concurrent inserts will slip through.

---

### Hazard 3 — Lab results extensibility

**Do not use joined table inheritance.** The original plan (`pcm_tem_samples`, `bulk_samples` as separate child tables) hardcodes the sample type taxonomy into the schema — adding LDW or any new type requires a migration and new model code.

**Use the config+data meta-model instead** (see Phase 4). Sample types, subtypes, unit types, and turnaround options are rows in admin-managed tables. The data tables (`sample_batches`, `sample_batch_units`) are fixed in shape regardless of how many types are defined.

**Validation that was structural is now app-layer:** `sample_unit_type.sample_type_id` must match `batch.sample_type_id` — enforce this in the service on create and return 422 if violated. This is a straightforward check and keeps the schema clean.

**Pitfall:** Don't enforce `allows_multiple_inspectors` at the DB level — a check constraint here would be complex and fragile. Enforce it in the service: if `sample_type.allows_multiple_inspectors` is false, reject a second inspector insert with 409.

---

### Hazard 4 — Derived project status (complexity and performance)

Project status is a function of: WA presence, codes on WA, RFA status, deliverable statuses, employee license validity flags, and potentially contractor documents. Computing this on every request will be slow at dashboard scale.

**Recommendation:** Maintain a materialized status — either a `project_computed_status` row or a set of flag columns on `projects` — updated by a service call whenever any dependency changes. The function `recalculate_project_status(project_id)` should be called explicitly from every endpoint that mutates a relevant entity (deliverable updated, WA code added, RFA approved, etc.).

Don't use DB triggers for this — keep the logic in Python where it's testable and readable.

---

### Hazard 5 — Dashboard query performance

The dashboard views all filter on compound conditions. Without indexes, these will be slow the moment the table has any real data.

**Add at migration time, not later:**

- Composite index on `projects(status, assigned_manager_id)`
- Index on `project_deliverables(project_id, status)`
- Index on `manager_project_assignments(user_id, unassigned_at)` (for "currently assigned" queries)

---

### Hazard 6 — Audit trail for manager assignments

Don't model manager assignment as a single FK on `projects`. You need the full history. Model it as an append-only table:

| column                | type                 |
| --------------------- | -------------------- |
| `id`                  | PK                   |
| `project_id`          | FK                   |
| `user_id`             | FK                   |
| `assigned_at`         | TIMESTAMP            |
| `unassigned_at`       | TIMESTAMP (nullable) |
| `assigned_by_user_id` | FK                   |

"Currently assigned manager" = row where `unassigned_at IS NULL`. When reassigning: set `unassigned_at` on the current row and insert a new one — never update in-place.

---

### Hazard 7 — Circular imports in SQLAlchemy models

In a domain-driven layout, `projects/models.py` will reference `schools/models.py`, `users/models.py`, etc. SQLAlchemy `relationship()` calls with back-references across domain folders are a common source of circular import errors.

**Mitigation:** Use string-based class references in all relationships:

```python
relationship("School", back_populates="projects")
```

...rather than importing the class directly. Ensure all models are imported in a single place (e.g. `app/database.py` or `app/models/__init__.py`) before Alembic runs.

---

### Hazard 8 — `project_num` pattern enforcement

The `\d{2}-\d{3}-\d{4}` pattern must be enforced at two layers:

- **Pydantic schema**: use `@field_validator` with `re.match`
- **DB check constraint**: `CHECK (project_num ~ '^\d{2}-\d{3}-\d{4}$')` in the migration

The first 2 digits encoding the year and the middle 3 encoding work type suggests you may want utility functions to parse meaning from a project number — put those in `common/validators.py`.

---

### Design Note — WA Code Tables Split (project vs. building level)

Project-level and building-level codes are modelled as two separate table pairs rather than a single table with a nullable `project_school_link_id`. This was chosen because:

- **Uniqueness is natural.** Project-level codes use PK `(work_auth_id, wa_code_id)`. Building-level use PK `(work_auth_id, wa_code_id, project_school_link_id)`. No partial unique indexes or NULL-in-PK edge cases.
- **Billing logic is separate.** Building-level billing is `monitor_role_rate × time_entry_hours`. Project-level billing follows a different model. Keeping them in separate tables eliminates NULL-branching in every billing and status query.
- **Budgets belong to building codes only.** `work_auth_building_codes` carries a `budget` (Numeric) per `(work_auth_id, wa_code_id, project_school_link_id)`. When estimated billing exceeds this budget it is a blocking project flag requiring an RFA with a `budget_adjustment`.
- **`(project_id, school_id)` composite FK is NOT NULL** on building code tables, enforced at the DB level via a `ForeignKeyConstraint` to `project_school_links(project_id, school_id)`. This guarantees the school is actually linked to the project — an orphaned reference is structurally impossible. `project_school_links` remains a plain association table with no surrogate key; the composite FK references it directly.

**Table schemas:**

`work_auth_project_codes`: `(work_auth_id, wa_code_id)` PK · `fee` · `status` · `added_at`

`work_auth_building_codes`: `(work_auth_id, wa_code_id, project_id, school_id)` PK · composite FK `(project_id, school_id)` → `project_school_links` · `budget` · `status` · `added_at`

`rfa_project_codes`: `(rfa_id, wa_code_id)` PK · `action`

`rfa_building_codes`: `(rfa_id, wa_code_id, project_id, school_id)` PK · composite FK `(project_id, school_id)` → `project_school_links` · `action` · `budget_adjustment` (nullable — only populated when the RFA is resolving a budget overage)

RFA lifecycle timestamps (`submitted_at`, `resolved_at`) live on the `rfas` table. The code tables track current state only. The `rfas` + `rfa_*_codes` tables provide the full history.

The `WACodeLevel` enum on the `wa_codes` table (`project` \| `building`) is validated at the app layer on insert to ensure codes are never placed in the wrong table.

---

### Design Note — Query Performance and N+1

The two most common performance problems in SQLAlchemy apps at this scale, in order of how often they cause trouble:

**1. N+1 queries** — fetching a list of objects and then firing one query per object to load a relationship. The fix is always `lazy="selectin"` or an explicit `joinedload()` on the relationship. Already applied to `RFA.project_codes` and `RFA.building_codes`. Apply the same pattern whenever a list endpoint serializes nested objects.

**2. Missing indexes** — a query on an unindexed column reads every row in the table. SQLAlchemy automatically creates indexes for columns declared with `index=True` and for single-column FKs. Composite FKs and filter columns used in dashboard queries need explicit indexes added in migrations (see Hazard 5).

Joins on indexed columns are fast regardless of table size. The join-heavy schema in Phase 4 and Phase 6 is fine as long as FK columns are indexed. The dashboard endpoints in Phase 7 are where composite indexes matter most.

**To catch regressions early:** add a `query_counter` pytest fixture and assert query counts on list endpoints (see Phase 5). A list endpoint that was 2 queries and becomes 52 queries after a model change is caught in CI, not in production.

---

### Design Note — AuditMixin Scope

`AuditMixin` (`created_at`, `updated_at`, `created_by_id`, `updated_by_id`) is applied to all business entity models where "who was responsible for this change" is a meaningful question. The guiding rule: if a change to this record could have downstream consequences that someone would need to investigate later, it gets audit columns.

**Applied to:** `wa_codes`, `deliverables`, `work_auths`, `work_auth_project_codes`, `work_auth_building_codes`, `rfas`, `rfa_project_codes`, `rfa_building_codes`, `projects`, `employees`, `employee_roles`, `project_deliverables`, `project_building_deliverables`, `time_entries`, `sample_batches`, `sample_types` and all config sub-tables, `schools`, `contractors`, `hygienists`

**Not applied to:** `manager_project_assignments` (already a purpose-built append-only audit trail); `project_school_links`, `project_contractor_links`, `project_hygienist_links` (structural association tables managed via parent; parent's audit covers the action); `users`, `roles`, `permissions` (auth layer)

**System writes** use `SYSTEM_USER_ID` (a reserved seeded user with no valid password) so automated changes are distinguishable from human edits in the audit columns. The full edit history (every field value before/after every change) is deferred — see Follow-up Project — Full Audit Trail.

---

### Design Note — Time Entry and Sample Batch State Model

**`time_entries.status`** (3 values, added in Phase 4):

- `assumed` — system-created placeholder; `start_datetime`/`end_datetime` span midnight-to-midnight on `date_collected`; times not yet confirmed from daily logs
- `entered` — times manually input or confirmed by a manager from daily logs; any manager edit to an `assumed` entry flips it to `entered`
- `locked` — project closed; entry is read-only

`created_by_id == SYSTEM_USER_ID` is sufficient to distinguish system-created entries from manually entered ones. No `source` column is needed.

**Conflict handling:** Overlapping entries for the same employee are allowed to exist simultaneously. On overlap detection (at insert/update), the service creates `time_entry_conflict` system notes (Phase 3.6) on both conflicting entries. These notes are blocking — neither project can close until the conflict is resolved. When the overlap is cleared, the system notes auto-resolve. This allows both managers to record reported work while making the conflict visible and tracked.

**`sample_batches.status`** (3 values, added in Phase 4):

- `active` — normal state
- `discarded` — explicitly invalidated by a manager (e.g., falsified samples, COC error); excluded from billing calculations
- `locked` — project closed; read-only

**Orphan handling:** The `orphaned` status was dropped. Instead, deletion of a time entry that has `active` or `discarded` batches linked to it is blocked with a 409. Managers must reassign or delete those batches before the entry can be deleted. This is sufficient because time entries are logs of real work and are rarely deleted in practice.

---

### Design Note — Configurable Lab Results and the Sample Rates / Contracts Runway

`sample_rates` is designed now with a nullable `contract_id` so the billing retrofit is additive:

- **Now (no contracts):** rates have `contract_id = NULL`; one global rate schedule
- **When contracts land:** add `contracts` table, add nullable `contract_id` FK to `work_auths` (backfill with current contract), add contract-specific rows to `sample_rates`; rate lookup prefers contract-specific row, falls back to `contract_id IS NULL`

Rate resolution chain: `sample_batch_unit → batch → time_entry → project → work_auth → contract_id → sample_rates`

Rates are denormalized onto `sample_batch_units.unit_rate` at record time (same pattern as `work_auth_project_codes.fee` and `employee_roles.hourly_rate`) so historical batches are unaffected when contract rates change.

---

---

## Follow-up Project — User Notifications and @Mentions

> Deferred. The Notes system (Phase 3.6) is designed to accommodate this without schema changes. Notes store body text as-is; `@username` patterns are intentionally preserved for future parsing. Do not sanitize or strip them.

When implemented:

- `note_mentions` table — `(note_id, user_id, notified_at)`; populated by parsing `@username` patterns from note bodies on creation or edit; parser lives in `notes/service.py`
- Notification dispatch: when a `note_mentions` row is inserted, queue a notification to the mentioned user (delivery channel TBD — email / in-app / both)
- In-app notification center: `GET /users/me/notifications` — unread mentions and unread replies to notes the user has participated in; `PATCH /users/me/notifications/{id}/read` — mark as read
- This feature does not require changes to the `notes` table schema — it extends cleanly with one new table and a parser function

---

## Follow-up Project — Full Audit Trail

> Deferred. The four `AuditMixin` columns (`created_at`, `updated_at`, `created_by_id`, `updated_by_id`) give point-in-time accountability — who last changed a record and when. The full audit trail adds complete edit history: every field value before and after every change, queryable per entity.

- Choose an approach: **event sourcing** (append-only log table, each row = one change event) or **temporal tables** (shadow table per model holding row snapshots); temporal tables are simpler to query, event sourcing is more flexible for replaying state
- `audit_log` table — `id`, `table_name`, `record_id`, `changed_by_id` (FK → users), `changed_at`, `operation` (`INSERT` \| `UPDATE` \| `DELETE`), `old_values` (JSON), `new_values` (JSON)
- Populate via SQLAlchemy `after_bulk_update` / `after_insert` / `after_delete` session events, or via DB triggers if moving to PostgreSQL
- Expose as `GET /audit-log?table=time_entries&record_id=42` — returns full edit history for any record

---

## Follow-up Project — Billing

> Deferred from the main roadmap. The core app tracks project state end-to-end; billing is a secondary concern that reads from that state without blocking it.

- `calculate_billable_segments(employee_id, role_type, start_dt, end_dt) -> list[BillingSegment]` — rate-split function in `employees/service.py`; handles shifts crossing midnight and `employee_role` rate-change boundaries; needs exhaustive unit tests before connecting to any endpoint
- `check_building_code_budgets(project_id)` — for each active `work_auth_building_code`, compare sum of (`monitor_role_rate × time_entry_hours`) against `budget`; returns list of overages; budget overage on any building-level code is a **blocking** project flag requiring an RFA with `budget_adjustment`
- Wire billing flag into `project_flags` and `derive_project_status(project_id)` in Phase 5
- `GET /projects/{id}/billing-summary` — returns hours by role, segments, and budget vs. actual per building code

---

### Design Note — Contracts (deferred)

Project-level WA code fees and employee role rates are both tied to a long-running contract. Contracts are not modelled yet because only one contract is active and no new one is expected soon.

**When contracts are added**, the retrofit is additive:

1. Add a `contracts` table
2. Add a nullable `contract_id` FK to `work_auths` and backfill with the single current contract
3. `contract_id` on `employee_roles` can be derived from the WA at query time or stored directly

**No billing logic changes** because fees and rates are stored on their records at assignment time (`work_auth_project_codes.fee`, `employee_roles.hourly_rate`). The contract is audit context — not a live lookup. If fees were derived from a contract at query time instead, this retrofit would be a logic rewrite. Keep fees on the record.
