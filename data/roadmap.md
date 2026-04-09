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
│   └── service.py             # includes rate-split billing logic
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
│   └── service.py             # role validation, rate-split calculation
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

### Phase 2 — Projects Core + Relationships

- [x] `projects` table — model, migrations, full CRUD (`GET/POST/PATCH/DELETE /projects/`) with name search + pagination; `project_number` field with regex validation
- [x] `project_school_links` (M2M association table) — model, migration — _schools linked via `projects.schools` relationship_
- [x] `ProjectContractorLink` table (composite PK `project_id`+`contractor_id`, `is_current` flag, `assigned_at`) — model, migration
- [x] `project_hygienist_links` (FK, one hygienist per project) — model, migration
- [ ] `manager_project_assignments` (audit trail: `project_id`, `user_id`, `assigned_at`, `unassigned_at`, `assigned_by`) — model, migration
- [ ] `work_auths` table — model, migration, link to `projects`
- [ ] `work_auths <-> wa_codes` link table — model, migration (tracks which codes are on the WA, pending RFA, or approved)
- [ ] `project_deliverables` join table (project + deliverable definition + status enum) — model, migration

---

### Phase 3 — Time Entries

- [ ] `time_entries` model — columns: `date`, `start_time`, `end_time`, `employee_id`, `employee_role_id` (FK to specific role instance), `project_school_link_id`
- [ ] Service: validate that `employee_role` was active on `date` at time of insert
- [ ] Service: implement **rate-split calculation** for shifts crossing a rate-change boundary or midnight
- [ ] `POST /time-entries/` with full validation
- [ ] `PATCH /time-entries/{id}` — allow updating `start_time`/`end_time` after the fact (manager adds times from daily logs later)

---

### Phase 4 — Lab Results

- [ ] `sample_batches` parent table — `batch_num`, `is_report`, `time_entry_id`, `sample_type` discriminator
- [ ] `pcm_tem_samples` child table — monitor, date, quantity, time_started, time_relinquished, turnaround_time
- [ ] `bulk_samples` child table — date, PLM qty, NOB-PLM qty, NOB-PREP qty, NOB-TEM qty
- [ ] `bulk_sample_inspectors` join table — bulk sample to employee (multiple inspectors per COC)
- [ ] CRUD endpoints for each type via `/lab-results/`

---

### Phase 5 — Project Status Engine

- [ ] Define all status enums: `DeliverableStatus` (`pending_wa`, `pending_rfa`, `outstanding`, `under_review`, `approved`), `RFAStatus` (`not_submitted`, `under_review`, `approved`)
- [ ] Service: `derive_project_status(project_id)` — pure function inspecting WA codes, deliverable statuses, RFA status, and returning a computed status
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

### Hazard 1 — Billing rate split across midnight / rate boundaries _(HIGH RISK)_

The 11/30/25 5PM–3AM example is the hardest logic in the app. A shift can cross:

- A calendar day (always check `end_time < start_time`)
- A rate-change boundary (start of a new `employee_role` record)

**Recommendation:** Write this as a pure, well-unit-tested function in `employees/service.py`:

```python
def calculate_billable_segments(employee_id, role_type, start_dt, end_dt) -> list[BillingSegment]
```

It should return a list of `(hours, rate)` segments. Test it exhaustively with edge cases before connecting it to the API.

**Pitfall:** Storing `date` + `start_time` + `end_time` separately makes span math awkward. Consider storing `start_datetime` and `end_datetime` as `TIMESTAMP` internally, while still accepting/displaying date+time separately in the API.

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

### Design Note — WA Codes Status Tracking

The `wa_codes` on a `work_auth` can exist in one of several states: _not present_, _requested via RFA_, _pending RFA approval_, _active on WA_. This is not a simple boolean. Model the join table with an explicit status:

| column             | description                                                      |
| ------------------ | ---------------------------------------------------------------- |
| `work_auth_id`     | FK                                                               |
| `wa_code_id`       | FK                                                               |
| `status`           | enum: `active` \| `rfa_submitted` \| `rfa_approved` \| `removed` |
| `added_at`         | TIMESTAMP                                                        |
| `rfa_submitted_at` | TIMESTAMP (nullable)                                             |
| `rfa_approved_at`  | TIMESTAMP (nullable)                                             |

This makes the RFA workflow queryable without needing to reconstruct state from event logs.
