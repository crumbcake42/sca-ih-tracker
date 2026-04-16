# Session Handoff — 2026-04-16 (Phase 6 Session C complete)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**390 tests passing.** Phase 6 Session C is complete. Session D is next.

---

## What Was Done This Session

### Phase 6 Session C — Project status read-side

**`ProjectStatus` enum** added to `app/common/enums.py`:
- `SETUP` — no time entries recorded yet (no work has started on the project)
- `IN_PROGRESS` — work is recorded, deliverables still outstanding
- `BLOCKED` — unresolved blocking notes (highest priority; overrides all other states)
- `READY_TO_CLOSE` — no outstanding deliverables, no pending RFAs, no assumed entries
- `LOCKED` — project closed (used in Session D; not yet returned by derivation)

**`ProjectStatusRead` schema** added to `app/projects/schemas.py`:
```python
class ProjectStatusRead(BaseModel):
    project_id: int
    status: ProjectStatus
    has_work_auth: bool
    pending_rfa_count: int
    outstanding_deliverable_count: int
    unconfirmed_time_entry_count: int
    blocking_issues: list[BlockingIssue]
```

**`derive_project_status(project_id, db)`** added to `app/projects/services.py`. Pure function, no writes. Derivation priority:
1. `BLOCKED` if any unresolved blocking notes
2. `SETUP` if no time entries on the project
3. `READY_TO_CLOSE` if outstanding_deliverable_count == 0 AND pending_rfa_count == 0 AND unconfirmed_time_entry_count == 0
4. `IN_PROGRESS` otherwise

Uses a local import of `ProjectStatusRead` inside the function body to avoid a circular import (`services.py` → `schemas.py` → `enums.py` is fine, but `schemas.py` imports `BlockingIssue` from `notes.schemas`; keeping the import local avoids any module-load ordering issue).

**`GET /projects/{id}/status`** endpoint added to `app/projects/router/base.py`. Returns `ProjectStatusRead`. 404 if project not found.

**10 new tests**: 8 service tests in `TestDeriveProjectStatus` (`app/projects/tests/test_projects_service.py`) and 2 endpoint tests in `app/projects/tests/test_project_status.py`.

---

## Design Decisions Made This Session

### `SETUP` = no time entries, not "no work auth"

The initial instinct was to define `SETUP` as "no WA issued yet." Corrected before implementation: `SETUP` means no work has been recorded on the project (no time entries), which is the operationally meaningful threshold. A project can have a WA but no field work started and is still in setup. A project with time entries but no WA is unusual but is `IN_PROGRESS` (or `BLOCKED` if a gap note was emitted).

### `ProjectStatusRead` imported locally inside `derive_project_status`

`services.py` is imported by `router/base.py`, which imports `schemas.py`. If `services.py` also imported `schemas.py` at module level, Python resolves the import chain at startup and it works fine — but using a local import inside the function body avoids any fragility if the import order ever changes. No performance concern since `derive_project_status` is not a hot path.

---

## Next Step

**Phase 6 Session D — Project closure and record locking.**

- `lock_project_records(project_id, db, user_id)` in `app/projects/services.py`
  - First calls `get_blocking_notes_for_project()` → raises 409 with blocking issues if any
  - On success: transitions `time_entries` (`assumed`/`entered` → `locked`) and `active` `sample_batches` → `locked`
- `POST /projects/{id}/close` endpoint — calls `lock_project_records`; 409 with `blocking_issues` payload on refusal, 200 on success
- `status != locked` guards on update/delete endpoints for `time_entries` and `sample_batches` (422)
- Tests: closure blocked by unresolved note (409 + payload); closure succeeds and cascades lock; locked records reject edits with 422

See the "Session D" checklist in `data/roadmap.md` under Phase 6.
