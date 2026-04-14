# Session Handoff — 2026-04-14 (Phase 3.5 complete)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**All tests passing. Phase 3.5 (Audit Infrastructure) is complete. Next step: write audit tests, then resume Phase 4.**

### Phase 3.5 — What Was Done

**Step 1 — System user sentinel**
- `app/common/config.py`: `SYSTEM_USER_ID: int = 1` added as module-level constant (after `settings = Settings()`)
- `app/scripts/db.py`: system user inserted in `initialize()` between Role Configuration and admin User Check, so it gets `id=1` on a fresh DB. Username `"system"`, email `"system@system.internal"`, `hashed_password="!"` (impossible bcrypt hash). Assigned `SUPERADMIN` role (needed for FK; can't log in anyway).

**Step 2 — AuditMixin applied to all business entity models**

The following models had `AuditMixin` added (already had it before, no change: `School`, `Project`, `WorkAuth`, `RFA`, `User`):

| Model | File | Notes |
|-------|------|-------|
| `WACode` | `app/wa_codes/models.py` | |
| `Contractor` | `app/contractors/models.py` | |
| `Hygienist` | `app/hygienists/models.py` | |
| `Employee` | `app/employees/models.py` | |
| `EmployeeRole` | `app/employees/models.py` | |
| `Deliverable` | `app/deliverables/models.py` | |
| `ProjectDeliverable` | `app/deliverables/models.py` | still has `added_at` (different name, kept) |
| `ProjectBuildingDeliverable` | `app/deliverables/models.py` | still has `added_at` |
| `WorkAuthProjectCode` | `app/work_auths/models.py` | still has `added_at` |
| `WorkAuthBuildingCode` | `app/work_auths/models.py` | still has `added_at` |
| `RFAProjectCode` | `app/work_auths/models.py` | |
| `RFABuildingCode` | `app/work_auths/models.py` | |
| `TimeEntry` | `app/time_entries/models.py` | manual `created_at` removed before applying mixin |
| `SampleBatch` | `app/lab_results/models.py` | manual `created_at` removed before applying mixin |
| `SampleType` | `app/lab_results/models.py` | |
| `SampleSubtype` | `app/lab_results/models.py` | |
| `SampleUnitType` | `app/lab_results/models.py` | |
| `TurnaroundOption` | `app/lab_results/models.py` | |
| `SampleTypeRequiredRole` | `app/lab_results/models.py` | |
| `SampleTypeWACode` | `app/lab_results/models.py` | |

**NOT applied to** (per design): `manager_project_assignments`, `project_school_links`, `project_contractor_links`, `project_hygienist_links`, `users`, `roles`, `permissions`, `deliverable_wa_code_triggers`.

**Step 3 — Write endpoints wired**

Every POST/PATCH on an audited model now captures `current_user` and sets `created_by_id`/`updated_by_id`. The pattern used:

```python
# Before (decorator-level, no user capture):
@router.post("/", dependencies=[Depends(PermissionChecker(PermissionName.X))])
async def create_something(body: ..., db: ...):

# After (parameter-level, user captured):
@router.post("/")
async def create_something(
    body: ...,
    db: ...,
    current_user: User = Depends(PermissionChecker(PermissionName.X)),
):
    obj = Model(**body.model_dump(), created_by_id=current_user.id)
```

Endpoints without existing permission checks (employees, hygienists) got `Depends(get_current_user)` added.

**Batch import factory** (`app/common/factories.py`): `current_user = Depends(get_current_user)` added to `import_batch` function; `created_by_id=current_user.id` passed to model constructor.

Files changed in Step 3:
- `app/common/factories.py`
- `app/projects/router/base.py`
- `app/projects/router/deliverables.py`
- `app/work_auths/router/base.py`
- `app/work_auths/router/project_codes.py`
- `app/work_auths/router/building_codes.py`
- `app/work_auths/router/rfas.py`
- `app/employees/router/base.py`
- `app/hygienists/router/base.py`
- `app/time_entries/router.py`
- `app/lab_results/router/batches.py`
- `app/lab_results/router/config.py`

---

## Next Step — Audit Tests

Write tests to verify audit field wiring. All tests pass as of this session. Migration not yet generated (user handles migrations themselves — do not run `alembic` commands).

### What to write

**~12 new tests across 4 files:**

**`app/time_entries/tests/test_time_entries.py`** — add to existing file:
- POST creates entry with `created_by_id = authenticated user's id`
- PATCH sets `updated_by_id = authenticated user's id`

**`app/lab_results/tests/test_batches.py`** — add to existing file:
- POST creates batch with `created_by_id = authenticated user's id`
- PATCH sets `updated_by_id = authenticated user's id`

**`app/work_auths/tests/test_work_auths.py`** (if it exists) OR new file — add/create:
- POST work auth sets `created_by_id`
- PATCH work auth sets `updated_by_id`

**New file: `app/tests/test_audit.py`** (or similar top-level):
- Batch import (CSV upload) sets `created_by_id` on created records — test against any batch import endpoint (schools, employees, or wa_codes)
- System user sentinel: after setup, `users` table has a row with `id=1`, `username="system"`; `verify_password("anything", "!")` returns `False`

### What NOT to test
- Every endpoint individually (pattern is uniform, spot-check is enough)
- DELETE (records are gone)
- The AuditMixin SQL columns themselves (SQLAlchemy guarantees)

### How to find the test conftest/auth fixture
Read `conftest.py` and existing test files (`app/time_entries/tests/test_time_entries.py` or `app/lab_results/tests/test_batches.py`) to understand how `auth_headers` / `client` / authenticated user fixture is set up before writing.

---

## Phase 4 Remaining (after audit tests)

Do not start these until audit tests are done:
- `time_entries.source` and `time_entries.status` columns + migration
- `sample_batches.status` column + migration
- Make `sample_batches.time_entry_id` nullable + migration
- Overlap detection service (`flag_employee_overlaps`)
- Orphan detection service (`orphan_detached_batches`)
- `POST /lab-results/batches/quick-add` endpoint

---

## Design Decisions (carried forward)

### Time entry state model

Two new columns on `time_entries`:

**`source`** — immutable, set at creation:
- `manual` — entered by a manager; also set when a manager edits a system-created entry
- `system` — auto-created by quick-add; `created_by_id = SYSTEM_USER_ID`

**`status`** — mutable:
- `assumed` — system placeholder; times are implied
- `entered` — manually input or manager-confirmed
- `conflicted` — overlaps another time entry for the same employee; blocks project closure
- `locked` — project closed; read-only

When a manager edits a `source=system` entry: `source → manual`, `status → entered`. `created_by_id` stays as `SYSTEM_USER_ID` (immutable origin). `updated_by_id` = manager's ID.

### Sample batch status

New `status` column on `sample_batches`:
- `active` — normal
- `orphaned` — `time_entry_id` deleted; becomes NULL; blocks closure
- `discarded` — invalidated by manager
- `locked` — project closed; read-only

### Quick-add endpoint

`POST /lab-results/batches/quick-add`:
- Accepts `project_id`, `school_id`, `employee_id`, `date_collected`
- Calls `resolve_or_create_time_entry()`: finds or creates a placeholder (`source=system`, `status=assumed`, `created_by_id=SYSTEM_USER_ID`)
- Role resolution: first active role matching `sample_type_required_roles`; if none required, first active role on `date_collected`; 422 if no active role found
- Inspector resolution: first `inspector_id` used as time entry's `employee_id`

---

## Non-Obvious Technical Patterns

### `db.get()` is wrong for GET endpoints that serialize nested relationships

Use `select()` with `.execution_options(populate_existing=True)` instead. Applied in `app/lab_results/service.py`.

### FK validation in service functions that return early

SQLite does not enforce FK constraints by default. Any service function that conditionally returns early must explicitly check that FK targets exist via `db.get(TargetModel, fk_id)`. Applied in `app/lab_results/router/batches.py`.

### `PermissionChecker` returns the user

`PermissionChecker.__call__` returns the user object. Use `current_user: User = Depends(PermissionChecker(X))` to both enforce permissions and capture the user in one dependency — no redundant `get_current_user` call needed.
