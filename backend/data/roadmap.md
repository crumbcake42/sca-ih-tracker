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

### Phase 4 — Lab Results _(in progress)_

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

> **Design decision:** `source` column was dropped. `created_by_id == SYSTEM_USER_ID` already encodes whether an entry was system-created — a redundant column adds a migration with no new information.
>
> **Design decision:** `conflicted` status was dropped. Overlap is caught at insert/update time with a 422 (see below) rather than maintained as running state. Running state requires re-evaluating overlap on every delete and update, is complex to keep correct, and turns a minor data-entry mistake into a hard project-closure block for a small internal team.

- [ ] `time_entries.status` — `assumed` (system placeholder, times not yet confirmed) \| `entered` (times manually input or confirmed from daily logs) \| `locked` (project closed; read-only)
- [ ] When a manager edits a `status=assumed` entry, set `status → entered`; `created_by_id` stays as `SYSTEM_USER_ID` (immutable origin); `updated_by_id` = manager's user ID
- [ ] Overlap validation at insert/update: if the new entry's `(employee_id, start_datetime, end_datetime)` overlaps any existing entry for that employee, return 422 with a clear message identifying the conflict — no `conflicted` status, no reactive re-evaluation
- [ ] `sample_batches.status` — `active` \| `discarded` \| `locked` (migration adds column)
- [ ] Make `sample_batches.time_entry_id` nullable (migration)
- [ ] Block deletion of `time_entries` that have `active` or `discarded` batches (409 with explanation) — simpler than orphan detection; managers rarely delete time entries in practice

**Quick-add endpoint** (manager-facing; no pre-existing time entry required):

- [ ] `POST /lab-results/batches/quick-add` — accepts `project_id`, `school_id`, `employee_id`, `date_collected` instead of `time_entry_id`; calls `resolve_or_create_time_entry()` which finds an existing entry for that employee/project/school/date or creates a placeholder (`status=assumed`, span = `date_collected 00:00` → `date_collected+1 00:00`, `created_by_id=SYSTEM_USER_ID`)
- [ ] Role resolution for system-created entries: use the first active role matching any `sample_type_required_roles` for the batch's sample type; if no required roles, use the employee's first active role on `date_collected`; 422 if no active role found
- [ ] Inspector resolution: use the first `inspector_id` in the list as the time entry's `employee_id`

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

- [ ] Service: `recalculate_deliverable_sca_status(project_id)` — updates `sca_status` on all `project_deliverables` and `project_building_deliverables` rows where status is still derivable (`pending_wa`, `pending_rfa`, `outstanding`); called from any endpoint that mutates WA, WA codes, or RFA resolution; `under_review` / `rejected` / `approved` are manual and never overwritten
- [ ] Wire `recalculate_deliverable_sca_status()` into: `POST /work-auths/`, `POST /work-auths/{id}/project-codes`, `POST /work-auths/{id}/building-codes`, `PATCH /work-auths/{id}/rfas/{rfa_id}` (on resolve)
- [ ] Service: `ensure_deliverables_exist(project_id)` — checks `deliverable_wa_code_triggers` and inserts any missing deliverable rows; called from time entry and lab result creation so deliverables are tracked as soon as work is recorded, before the WA exists
- [ ] **Gap from design doc:** when a batch is recorded, check `sample_type_wa_codes` for the batch's sample type and surface any WA codes not yet on the project's WA as a project flag ("needs RFA to add LAMP30, LAMP32"); the `sample_type_wa_codes` table and FK are already in place — this wiring is not yet planned as a concrete task
- [ ] Service: `derive_project_status(project_id)` — pure function inspecting WA codes, deliverable statuses, pending RFAs, and unconfirmed time entries; returns computed status
- [ ] Implement `project_flags` — a project can carry multiple non-blocking notes and blocking issues simultaneously; **blocking flags include:**
  - Any `time_entry` linked to this project with `status=assumed` — placeholder times not yet confirmed from daily logs
  - Any `sample_batch` linked to this project with `status=discarded` that has not been reviewed _(exact semantics TBD)_
- [ ] Service: `lock_project_records(project_id)` — called on project closure; transitions all linked `time_entries` from `assumed`/`entered` → `locked` and all linked `sample_batches` from `active` → `locked`; locked records are read-only; guards on update endpoints check `status != locked` before allowing changes
- [ ] Wire status derivation into project update endpoints
- [ ] `GET /projects/{id}/status` — returns full status breakdown including any blocking flags

---

### Phase 7 — Dashboard Query Endpoints

- [ ] `GET /projects/dashboard/my-outstanding-deliverables`
- [ ] `GET /projects/dashboard/needs-rfa`
- [ ] `GET /projects/dashboard/rfa-pending`
- [ ] `GET /projects/dashboard/ready-to-bill`
- [ ] `GET /projects/dashboard/awaiting-contractor-doc`
- [ ] Add composite DB indexes to support these queries (see Hazards section)

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

**`time_entries`** carry two orthogonal fields added in Phase 4:

`source` (immutable, set at creation):
- `manual` — entered by a manager from activity logs; also set when a manager edits a system-created entry
- `system` — auto-created by the quick-add endpoint on behalf of a lab sample receipt; `created_by_id = SYSTEM_USER_ID`

`status` (mutable):
- `assumed` — system placeholder; `start_datetime`/`end_datetime` are implied (00:00–00:00), not confirmed
- `entered` — manually input or manager-confirmed; times are intentional
- `conflicted` — overlaps with another time entry for the same employee on any project; both entries are flagged; neither project can close until the conflict is resolved
- `locked` — project has been closed; entry is read-only and excluded from billing recalculation

When a manager edits a `source=system` entry, `source` flips to `manual` and `status` advances to `entered`. `created_by_id` stays as `SYSTEM_USER_ID` — it records the origin, not the last editor.

**`sample_batches`** carry a `status` field:
- `active` — linked to a valid, non-locked time entry
- `orphaned` — `time_entry_id` was deleted or revised such that `date_collected` no longer falls within the entry's span; `time_entry_id` becomes `NULL`; orphaned batches block project closure until re-linked or discarded
- `discarded` — explicitly invalidated by a manager (e.g., falsified samples, COC error); excluded from billing calculations
- `locked` — project closed; read-only

Overlap detection (`flag_employee_overlaps`) and orphan detection (`orphan_detached_batches`) run as service calls on every time entry write, not as DB triggers, so they are testable and readable. See Phase 4.

---

### Design Note — Configurable Lab Results and the Sample Rates / Contracts Runway

`sample_rates` is designed now with a nullable `contract_id` so the billing retrofit is additive:

- **Now (no contracts):** rates have `contract_id = NULL`; one global rate schedule
- **When contracts land:** add `contracts` table, add nullable `contract_id` FK to `work_auths` (backfill with current contract), add contract-specific rows to `sample_rates`; rate lookup prefers contract-specific row, falls back to `contract_id IS NULL`

Rate resolution chain: `sample_batch_unit → batch → time_entry → project → work_auth → contract_id → sample_rates`

Rates are denormalized onto `sample_batch_units.unit_rate` at record time (same pattern as `work_auth_project_codes.fee` and `employee_roles.hourly_rate`) so historical batches are unaffected when contract rates change.

---

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
