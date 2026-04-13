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
│   ├── models.py              # SampleBatch (parent), PCMTEMSample, BulkSample, etc.
│   ├── router.py
│   ├── schemas.py
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

### Phase 4 — Lab Results

- [ ] `sample_batches` parent table — `batch_num`, `is_report`, `time_entry_id`, `sample_type` discriminator
- [ ] `pcm_tem_samples` child table — monitor, date, quantity, time_started, time_relinquished, turnaround_time
- [ ] `bulk_samples` child table — date, PLM qty, NOB-PLM qty, NOB-PREP qty, NOB-TEM qty
- [ ] `bulk_sample_inspectors` join table — bulk sample to employee (multiple inspectors per COC)
- [ ] CRUD endpoints for each type via `/lab-results/`

---

### Phase 5 — Project Status Engine

- [ ] Service: `recalculate_deliverable_sca_status(project_id)` — updates `sca_status` on all `project_deliverables` and `project_building_deliverables` rows where status is still derivable (`pending_wa`, `pending_rfa`, `outstanding`); called from any endpoint that mutates WA, WA codes, or RFA resolution; `under_review` / `rejected` / `approved` are manual and never overwritten
- [ ] Wire `recalculate_deliverable_sca_status()` into: `POST /work-auths/`, `POST /work-auths/{id}/project-codes`, `POST /work-auths/{id}/building-codes`, `PATCH /work-auths/{id}/rfas/{rfa_id}` (on resolve)
- [ ] Service: `ensure_deliverables_exist(project_id)` — checks `deliverable_wa_code_triggers` and inserts any missing deliverable rows; called from time entry and lab result creation (Phase 3/4) so deliverables are tracked as soon as work is recorded, before the WA exists
- [ ] Service: `derive_project_status(project_id)` — pure function inspecting WA codes, deliverable statuses, pending RFAs, and returning a computed status
- [ ] Implement `project_flags` — a project can have multiple non-blocking notes and blocking issues simultaneously
- [ ] Wire status derivation into project update endpoints
- [ ] `GET /projects/{id}/status` — returns full status breakdown

---

### Phase 6 — Dashboard Query Endpoints

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

### Hazard 3 — Lab results polymorphism

**Recommendation: Joined table inheritance** (SQLAlchemy supports this natively).

Single table inheritance (one table, many NULLs) is tempting but becomes a mess as sample types grow. Joined inheritance gives you a clean `sample_batches` parent you can query uniformly while each subtype has its own normalized table. The `sample_type` discriminator column on the parent drives which child to join.

**Pitfall:** Don't try to store bulk sample inspector relationships in a column. `bulk_sample_inspectors` must be a proper join table.

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
