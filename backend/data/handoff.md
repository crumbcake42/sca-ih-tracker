# Session Handoff — 2026-04-14 (Documentation pass complete; Phase 4 still next)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**All tests passing. Phase 3.5 is fully done. Phase 4 design was revised last session. This session was a documentation pass — no code was changed. Next step is still Phase 4 migration and state model.**

---

## What Was Done This Session

### Documentation pass — module READMEs written

Nine `README.md` files were created across the project. Each follows the three-section format from `data/roadmap.md`: **Purpose**, **Non-obvious behavior**, **Before you modify**. Mermaid diagrams are embedded in modules with state machines or validation chains.

| File | Key content |
|------|-------------|
| `app/employees/README.md` | Time-bound EmployeeRole, app-layer overlap validation, nullable user link |
| `app/users/README.md` | PermissionChecker returns the user, SYSTEM_USER_ID=1 is reserved, RBAC structure |
| `app/wa_codes/README.md` | WACodeLevel drives endpoint gating + deliverable granularity; treat level as immutable once in use |
| `app/deliverables/README.md` | Dual independent status tracks, trigger config is seeded not dynamic, separate project/building tables |
| `app/common/README.md` | AuditMixin is explicit-only, SYSTEM_USER_ID import location, router factory functions |
| `app/work_auths/README.md` | WA code status state machine (Mermaid), RFA state machine (Mermaid), one-pending-RFA-per-WA rule |
| `app/projects/README.md` | Link tables via project endpoints only, ProjectManagerAssignment is append-only audit trail, composite FK dependencies |
| `app/time_entries/README.md` | Planned state diagram (Mermaid, status col not yet added), overlap → system notes not 422, SYSTEM_USER_ID identifies quick-add entries |
| `app/lab_results/README.md` | Config vs data layer, batch validation chain flowchart (Mermaid), sample_unit_type validation is app-layer only |

The roadmap's "Files to generate" checklist was updated. Still unchecked: `backend/README.md`, `backend/app/PATTERNS.md` (already exists), `backend/app/notes/README.md` (blocked until Phase 3.6 implements the notes module).

Thin CRUD modules (schools, contractors, hygienists) were deliberately skipped per the roadmap's own rule.

---

---

## Design Decisions (permanent — carry forward)

### `time_entries.source` — DROPPED

The planned `source` column (`manual` | `system`) is redundant. `created_by_id == SYSTEM_USER_ID` already encodes whether an entry was system-created. Do not add this column.

### `conflicted` status — DROPPED

The planned `conflicted` status value and `flag_employee_overlaps` service are removed. The original intent was to detect when two time entries for the same employee overlap and block project closure until resolved.

**Why dropped:** Maintaining `conflicted` as running state requires re-evaluating overlap on every create, update, and delete — querying all entries for an employee, updating flags, and coordinating with the `locked` transition. It's complex, easy to get wrong, and turns a minor data-entry mistake into a hard project-closure block for a small internal team.

**Replacement:** Validate at insert/update time. If the new/updated entry's time span overlaps an existing entry for the same employee, return 422 with a clear message identifying the conflict. No `conflicted` status. No reactive service. The error appears at the point of entry, not later as a blocking flag on the project.

### `orphaned` batch status + `orphan_detached_batches` — DROPPED

The planned `orphaned` status value and `orphan_detached_batches` service (which would mark batches orphaned when their time entry was deleted or its span changed past the collection date) are removed.

**Why dropped:** Time entries are rarely deleted in practice — they're logs of work done. The scenario that triggers orphaning (modifying a time entry's date range far enough that the collection date no longer falls within it) is an edge case not described in the original requirements.

**Replacement:** Block deletion of `time_entries` that have `active` or `discarded` batches with a 409 ("this entry has X batches linked to it — reassign or delete them first"). No orphan state to manage.

### Revised state models

**`time_entries.status`** (3 values, down from 4):
- `assumed` — system placeholder; times not yet confirmed from daily logs
- `entered` — times manually input or confirmed by a manager
- `locked` — project closed; read-only

When a manager edits a `status=assumed` entry: `status → entered`. `created_by_id` stays as `SYSTEM_USER_ID`. `updated_by_id` = manager's ID.

**`sample_batches.status`** (3 values, down from 4):
- `active` — normal
- `discarded` — invalidated by manager
- `locked` — project closed; read-only

### Phase 5 (Observability) — DEFERRED

Deferred until the app is deployed and real performance data is available. Do not implement before Phase 6.

---

## Next Step — Phase 4 Completion

One migration covers all three schema changes. Implement them together:

1. **`time_entries.status`** — add `TimeEntryStatus` enum (`assumed`, `entered`, `locked`); add nullable column with default `entered` (existing manual entries are already confirmed); add server_default as well so the DB column has a fallback
2. **`sample_batches.status`** — add `SampleBatchStatus` enum (`active`, `discarded`, `locked`); add column with default `active`
3. **`sample_batches.time_entry_id` nullable** — remove `NOT NULL` constraint

After migration: update `PATCH /time-entries/{id}` to flip `assumed → entered` on any manager edit. Add 409 guard to `DELETE /time-entries/{id}` if active/discarded batches exist. Add overlap 422 to `POST` and `PATCH` time entry endpoints.

Then: implement `POST /lab-results/batches/quick-add`.

**Do not start Phase 6 until the quick-add endpoint is working and tested.**

---

## Non-Obvious Technical Patterns

### `db.get()` is wrong for GET endpoints that serialize nested relationships

Use `select()` with `.execution_options(populate_existing=True)` instead. Applied in `app/lab_results/service.py`.

### FK validation in service functions that return early

SQLite does not enforce FK constraints by default. Any service function that conditionally returns early must explicitly check that FK targets exist via `db.get(TargetModel, fk_id)`. Applied in `app/lab_results/router/batches.py`.

### `PermissionChecker` returns the user

`PermissionChecker.__call__` returns the user object. Use `current_user: User = Depends(PermissionChecker(X))` to both enforce permissions and capture the user in one dependency — no redundant `get_current_user` call needed.

### Audit field testing pattern

Audit fields (`created_by_id`, `updated_by_id`) are not in any Read schemas, so they can't be checked from response JSON. After an API call via `auth_client`, query `db_session` directly:

```python
obj = await db_session.get(Model, response.json()["id"])
assert obj.created_by_id == 1  # fake_user.id from auth_client fixture
```

Or for an object already in scope, use `await db_session.refresh(obj)` then check the field.

### User-managed migrations

Do not run `alembic` commands. The user generates and applies all migrations themselves.
