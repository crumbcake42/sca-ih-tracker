# Session Handoff — 2026-04-14 (Phase 4 fully implemented; migration pending)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**307 tests passing. Phase 4 code is fully implemented. One Alembic migration is still needed before the changes work against a real DB — the user generates and applies all migrations manually.**

**Migration label:** `add_status_enums_nullable_batch_time_entry`

**Three schema changes in one migration:**

1. `ALTER TABLE time_entries ADD COLUMN status VARCHAR NOT NULL DEFAULT 'entered'`
2. `ALTER TABLE sample_batches ADD COLUMN status VARCHAR NOT NULL DEFAULT 'active'`
3. Make `sample_batches.time_entry_id` nullable (SQLite: recreate table)

---

## What Was Done This Session

### Phase 4 implementation

All Phase 4 code written and tested (307 passing, up from 278):

- `TimeEntryStatus` + `SampleBatchStatus` enums added to `app/common/enums.py`
- `time_entries.status` column added (default `entered`)
- `sample_batches.status` column added (default `active`)
- `sample_batches.time_entry_id` made nullable in model + schema
- `check_time_entry_overlap()` service function — 422 on cross-project overlap; NULL end treated as full-day
- PATCH `/time-entries/{id}` flips `assumed → entered` on any manager edit
- DELETE `/time-entries/{id}` returns 409 if active/discarded batches are linked
- `POST /lab-results/batches/{id}/discard` endpoint added
- `POST /lab-results/batches/quick-add` endpoint added (atomic time entry + batch creation)
- New test classes: `TestTimeEntryStatus`, `TestTimeEntryOverlap`, `TestDeleteTimeEntryGuard`, `TestDiscardBatch`, `TestNullableTimeEntry`, `TestQuickAdd`

### Also this session

- `/gnight` slash command created at `.claude/commands/gnight.md`
- CLAUDE.md updated: use `.venv/Scripts/python.exe -m pytest` (not `source activate`)

### Documentation pass (prior session)

Nine `README.md` files were created across the project. Each follows the three-section format from `data/roadmap.md`: **Purpose**, **Non-obvious behavior**, **Before you modify**. Mermaid diagrams are embedded in modules with state machines or validation chains.

| File                         | Key content                                                                                                                            |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `app/employees/README.md`    | Time-bound EmployeeRole, app-layer overlap validation, nullable user link                                                              |
| `app/users/README.md`        | PermissionChecker returns the user, SYSTEM_USER_ID=1 is reserved, RBAC structure                                                       |
| `app/wa_codes/README.md`     | WACodeLevel drives endpoint gating + deliverable granularity; treat level as immutable once in use                                     |
| `app/deliverables/README.md` | Dual independent status tracks, trigger config is seeded not dynamic, separate project/building tables                                 |
| `app/common/README.md`       | AuditMixin is explicit-only, SYSTEM_USER_ID import location, router factory functions                                                  |
| `app/work_auths/README.md`   | WA code status state machine (Mermaid), RFA state machine (Mermaid), one-pending-RFA-per-WA rule                                       |
| `app/projects/README.md`     | Link tables via project endpoints only, ProjectManagerAssignment is append-only audit trail, composite FK dependencies                 |
| `app/time_entries/README.md` | Planned state diagram (Mermaid, status col not yet added), overlap → 422 not system notes, SYSTEM_USER_ID identifies quick-add entries |
| `app/lab_results/README.md`  | Config vs data layer, batch validation chain flowchart (Mermaid), sample_unit_type validation is app-layer only                        |

---

## Design Decisions (permanent — carry forward)

### `time_entries.source` — DROPPED

`created_by_id == SYSTEM_USER_ID` already encodes whether an entry was system-created. Do not add this column.

### `conflicted` status — DROPPED (replaced with 422 at entry time)

No `conflicted` status. No reactive service. If a POST or PATCH time entry would overlap an existing entry for the same employee (cross-project), return 422 with the conflicting entry's ID. Error appears at the point of entry.

### `orphaned` batch status + `orphan_detached_batches` — DROPPED

Block deletion of `time_entries` that have `active` or `discarded` batches with 409. No orphan state to manage.

### Revised state models

**`time_entries.status`** (3 values):

- `assumed` — system placeholder; times not yet confirmed (always created with `start_datetime` at midnight 00:00:00 of the date, `end_datetime=None`)
- `entered` — times manually input or confirmed by a manager
- `locked` — project closed; read-only

When a manager edits a `status=assumed` entry: `status → entered`. `created_by_id` stays as `SYSTEM_USER_ID`. `updated_by_id` = manager's ID. Default for new manager-created entries: `entered`.

**`sample_batches.status`** (3 values):

- `active` — normal
- `discarded` — invalidated by manager (via dedicated `POST /batches/{id}/discard` endpoint)
- `locked` — project closed; read-only

### NULL end_datetime — assumed entries only

`end_datetime` being NULL is valid only on `assumed` entries. These are always created with `start_datetime = 00:00:00` of the work date. For overlap checking, treat NULL end_datetime as midnight of the next day (`DATETIME(start_datetime, '+1 day')`), which works correctly because start is always at midnight.

### Dismissable requirements — NEW CONCEPT, deferred to after Phase 6

A batch with `time_entry_id=null` is a blocking issue (samples exist but can't be attributed to valid work time). Managers should be able to dismiss such issues, explicitly acknowledging the problem and excluding those samples from billing. Needs design: storage, permissions, billing integration. `time_entry_id` nullable (added in Phase 4 migration) is the prerequisite.

### Phase 5 (Observability) — DEFERRED

Deferred until the app is deployed and real performance data is available. Do not implement before Phase 6.

### Batch discard — dedicated endpoint, not PATCH field

`POST /lab-results/batches/{id}/discard` rather than adding `status` to `SampleBatchUpdate`. Keeps the schema clean; allows future reason/note fields.

---

## Next Step — Phase 3.6 (Notes and Blockers)

Phase 3.6 is the prerequisite for Phase 6 (project closure). Now that Phase 4 is done, Phase 3.6 is the natural next step. Key design is already in `data/roadmap.md` under Phase 3.6. The main work:

1. `notes` table — polymorphic (`entity_type` + `entity_id`), `is_blocking`, `is_resolved`, system vs. user notes
2. Service functions: `create_system_note()`, `auto_resolve_system_notes()`, `get_blocking_notes_for_project()`
3. Endpoints: `GET/POST /notes/{entity_type}/{entity_id}`, `POST /notes/{id}/reply`, `PATCH /notes/{id}/resolve`
4. `GET /projects/{id}/blocking-issues`

**Do not start Phase 6 until Phase 3.6 is complete.**

---

## Phase 4 Implementation — Full Plan (complete — kept for reference)

### Files to modify

| File                                | Change                                                                 |
| ----------------------------------- | ---------------------------------------------------------------------- | -------------------- |
| `app/common/enums.py`               | Add `TimeEntryStatus`, `SampleBatchStatus`                             |
| `app/time_entries/models.py`        | Add `status` column                                                    |
| `app/time_entries/schemas.py`       | Add `status` to `TimeEntryRead` only                                   |
| `app/time_entries/service.py`       | Add `check_time_entry_overlap()`                                       |
| `app/time_entries/router.py`        | POST/PATCH overlap check; PATCH assumed→entered flip; DELETE 409 guard |
| `app/lab_results/models.py`         | Add `status` column; make `time_entry_id` nullable                     |
| `app/lab_results/schemas.py`        | Add `status` to `SampleBatchRead`; `time_entry_id: int                 | None` in Create/Read |
| `app/lab_results/router/batches.py` | Add `POST /{batch_id}/discard`; add `POST /quick-add`                  |
| `app/lab_results/service.py`        | Add helpers for discard and quick-add                                  |

### Step 1 — Enums (`app/common/enums.py`)

```python
class TimeEntryStatus(StrEnum):
    ASSUMED = "assumed"
    ENTERED = "entered"
    LOCKED  = "locked"

class SampleBatchStatus(StrEnum):
    ACTIVE    = "active"
    DISCARDED = "discarded"
    LOCKED    = "locked"
```

### Step 2 — Models

`app/time_entries/models.py`:

```python
status: Mapped[TimeEntryStatus] = mapped_column(
    SQLEnum(TimeEntryStatus), nullable=False,
    default=TimeEntryStatus.ENTERED, server_default=TimeEntryStatus.ENTERED,
)
```

`app/lab_results/models.py`:

```python
# Add status:
status: Mapped[SampleBatchStatus] = mapped_column(
    SQLEnum(SampleBatchStatus), nullable=False,
    default=SampleBatchStatus.ACTIVE, server_default=SampleBatchStatus.ACTIVE,
)
# Make time_entry_id nullable:
time_entry_id: Mapped[int | None] = mapped_column(
    ForeignKey("time_entries.id", ondelete="RESTRICT"), index=True, nullable=True
)
time_entry: Mapped["TimeEntry | None"] = relationship("TimeEntry", ...)
```

### Step 3 — Migration (user runs manually)

Three changes in one migration:

1. `ALTER TABLE time_entries ADD COLUMN status VARCHAR NOT NULL DEFAULT 'entered'`
2. `ALTER TABLE sample_batches ADD COLUMN status VARCHAR NOT NULL DEFAULT 'active'`
3. Make `sample_batches.time_entry_id` nullable (SQLite: recreate table)

### Step 4 — Schemas

- `TimeEntryRead`: add `status: TimeEntryStatus`
- Do NOT add status to `TimeEntryCreate` or `TimeEntryUpdate`
- `SampleBatchRead`: add `status: SampleBatchStatus`; change `time_entry_id: int | None`
- `SampleBatchCreate`: change `time_entry_id: int | None = None`
- Do NOT add status to `SampleBatchUpdate`

### Step 5 — Overlap service function (`app/time_entries/service.py`)

```python
async def check_time_entry_overlap(
    employee_id: int, start_dt: datetime, end_dt: datetime | None,
    db: AsyncSession, exclude_id: int | None = None,
) -> None:
    from datetime import timedelta
    effective_new_end = end_dt if end_dt is not None else datetime.combine(
        start_dt.date() + timedelta(days=1), time.min
    )
    stmt = select(TimeEntry).where(
        TimeEntry.employee_id == employee_id,
        TimeEntry.start_datetime < effective_new_end,
        func.coalesce(
            TimeEntry.end_datetime,
            func.datetime(TimeEntry.start_datetime, "+1 day")
        ) > start_dt,
    )
    if exclude_id is not None:
        stmt = stmt.where(TimeEntry.id != exclude_id)
    result = await db.execute(stmt)
    conflict = result.scalars().first()
    if conflict:
        raise HTTPException(422, detail=f"Time entry overlaps with existing entry {conflict.id}.")
```

### Step 6 — Time entry router changes (`app/time_entries/router.py`)

- **POST**: call `check_time_entry_overlap(body.employee_id, body.start_datetime, body.end_datetime, db)` after existing validations
- **PATCH**: call `check_time_entry_overlap(entry.employee_id, effective_start, effective_end, db, exclude_id=entry.id)`, then flip `if entry.status == TimeEntryStatus.ASSUMED: entry.status = TimeEntryStatus.ENTERED`
- **DELETE**: query `COUNT(*) FROM sample_batches WHERE time_entry_id = id AND status IN ('active','discarded')` → 409 if > 0

### Step 7 — Batch discard endpoint (`app/lab_results/router/batches.py`)

`POST /lab-results/batches/{id}/discard` — permission: PROJECT_EDIT

- 404 if not found
- 422 if status == locked ("Cannot discard a locked batch")
- 422 if status == discarded ("Batch is already discarded")
- Set status → discarded, commit, return 200 SampleBatchRead

### Step 8 — Quick-add endpoint

`POST /lab-results/batches/quick-add` — permission: PROJECT_EDIT

New schema `QuickAddBatchCreate`: all `SampleBatchCreate` fields except `time_entry_id`, plus `employee_id`, `employee_role_id`, `project_id`, `school_id`, `date`.

Service `quick_add_batch()`:

1. Validate employee, project, school link, role (reuse from `app/time_entries/service.py`)
2. Run `check_time_entry_overlap` for assumed entry (midnight to midnight of date)
3. Create `TimeEntry` with `status=assumed`, `created_by_id=SYSTEM_USER_ID`
4. Create `SampleBatch` linked to new time entry
5. Run batch validators (reuse from `app/lab_results/service.py`)
6. Commit; return `SampleBatchRead`

### Tests to write/update

`app/time_entries/test_time_entries.py`:

- Update all response assertions to handle new `status` field
- `TestTimeEntryStatus`: POST → status=entered; manually set assumed in DB, PATCH → status flips to entered
- `TestTimeEntryOverlap`: same employee overlap → 422; different employee → 201; back-to-back → 201; PATCH into/out of overlap; assumed entry (NULL end) treated as full day
- `TestDeleteTimeEntryGuard`: no batches → 204; active batch → 409; discarded batch → 409

`app/lab_results/tests/test_batches.py`:

- Update response assertions for new `status` field (default active)
- `TestDiscardBatch`: discard active → 200; already discarded → 422; missing → 404
- `TestNullableTimeEntry`: create batch with `time_entry_id=null` → 201

`app/lab_results/tests/test_quick_add.py` (new file):

- Happy path: time entry + batch created atomically; status=assumed; created_by_id=SYSTEM_USER_ID
- Missing employee → 404
- Overlap on date → 422
- Invalid batch fields → 422

---

## Non-Obvious Technical Patterns

### `db.get()` is wrong for GET endpoints that serialize nested relationships

Use `select()` with `.execution_options(populate_existing=True)` instead. Applied in `app/lab_results/service.py`.

### FK validation in service functions that return early

SQLite does not enforce FK constraints by default. Validate FK targets via `db.get(TargetModel, fk_id)` in any service function that returns early.

### `PermissionChecker` returns the user

`current_user: User = Depends(PermissionChecker(X))` — no separate `get_current_user` call needed.

### Audit field testing pattern

Audit fields are not in Read schemas. After an API call, query `db_session` directly:

```python
obj = await db_session.get(Model, response.json()["id"])
assert obj.created_by_id == 1
```

### User-managed migrations

Do not run `alembic` commands. The user generates and applies all migrations themselves.
