# Session Handoff — 2026-04-22 (Phase 1.5 planning complete)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**401 tests passing.** Phase 6 is fully complete. Phase 1.5 (thin CRUD backfill) is next; Phase 6.5 follows.

---

## What Was Done This Session

### Phase 1.5 planning — thin CRUD backfill decision

No code written. Audited every entity module to assess whether a generic `create_basic_crud_router` factory was worth building. Decided against it — see `ROADMAP.md` Phase 1.5 for the full rationale. Added Phase 1.5 to the roadmap and updated the next-step pointer in this file.

**Key decision:** CSV batch import and individual POST endpoints coexist on all entities. Batch import is a convenience for bulk seeding, not a restriction — every entity should have individual create/edit endpoints too.

---

## Previous Session — Phase 6 Session D — Project closure and record locking

**`Project.is_locked: bool`** added to `app/projects/models/base.py`:
- `server_default="0"`, `default=False`
- **Migration required** — user must generate and apply before running the app against a real DB

**`lock_project_records(project_id, db, user_id)`** added to `app/projects/services.py`:
- Calls `get_blocking_notes_for_project()` → raises `HTTPException(409, detail={"blocking_issues": [...]})` if any unresolved
- Bulk-updates `time_entries` (assumed/entered → locked) via `update()` with `execution_options(synchronize_session=False)`
- Bulk-updates `active` `sample_batches` linked to those time entries → locked (same pattern)
- Sets `project.is_locked = True` and `project.updated_by_id = user_id`

**`derive_project_status`** updated: short-circuits to `ProjectStatus.LOCKED` (with all counts zeroed) when `project.is_locked` is True.

**`POST /projects/{id}/close`** added to `app/projects/router/base.py`:
- 404 if project not found
- 409 if already closed
- Calls `lock_project_records` (which 409s on blocking issues), then commits
- Returns `ProjectStatusRead` (status=LOCKED) on success

**Locked guards** added:
- `PATCH /time-entries/{id}` → 422 if `entry.status == LOCKED`
- `DELETE /time-entries/{id}` → 422 if `entry.status == LOCKED`
- `PATCH /lab-results/batches/{id}` → 422 if `batch.status == LOCKED`
- `DELETE /lab-results/batches/{id}` → 422 if `batch.status == LOCKED`
- (Discard endpoint already had a LOCKED check from Phase 4)

**11 new tests** in `app/projects/tests/test_project_closure.py`.

---

## Design Decisions Made This Session

### `is_locked` on `Project` rather than inferring from time entry statuses

A project with no time entries would have no locked entries after closure — inference is ambiguous. An explicit flag is unambiguous and makes `derive_project_status` a simple early return.

### `lock_project_records` raises `HTTPException` directly

Consistent with every other service function in this codebase (`validate_role_for_entry`, `check_time_entry_overlap`, etc.). The router doesn't need to re-wrap the error.

### Discarded batches are not re-locked

`lock_project_records` only transitions `ACTIVE → LOCKED`. Discarded batches stay discarded — they're already excluded from billing and are effectively read-only post-discard. Locking them too would change their status without adding any new constraint.

---

## Open Item (deferred, recorded in memory)

**Assumed entries at closure:** `lock_project_records` currently locks assumed entries silently. `unconfirmed_time_entry_count > 0` is already surfaced in `ProjectStatusRead`. Whether to make this a hard closure gate (block with 409) is deferred — the `READY_TO_CLOSE` status already requires zero assumed entries, so the UI can guide users before they hit close.

---

## Next Step

**Phase 1.5 — Thin CRUD Backfill.** Reference-table endpoints skipped during Phase 1. Each entity is its own session.

Suggested order:
1. `contractors` — greenfield (no CRUD router at all); largest gap
2. `schools` — add POST/PATCH alongside existing list + identifier GET
3. `wa_codes` — same shape as schools, plus level-immutability guard on PATCH
4. `employees` — `POST /employees/`, `PATCH /employees/{id}`; batch import stays as supplemental bulk path

Pattern to follow: `app/hygienists/router/base.py`. No factory — decision recorded in `ROADMAP.md` Phase 1.5.

After Phase 1.5, resume with **Phase 6.5 — Required Documents and Expected/Placeholder Entities** (full design in `ROADMAP.md`; the placeholder→actual matching layer is still design-not-finalized and needs a dedicated session before any implementation).
