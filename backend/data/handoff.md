# Session Handoff — 2026-04-13

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**269 tests passing. Phase 4 (Lab Results) is partially complete.**

What is done:
- All 9 lab results tables created and migrated (`sample_types`, `sample_subtypes`, `sample_unit_types`, `turnaround_options`, `sample_type_required_roles`, `sample_type_wa_codes`, `sample_batches`, `sample_batch_units`, `sample_batch_inspectors`)
- Full router at `/lab-results/config/sample-types` (config CRUD) and `/lab-results/batches` (data CRUD)
- Tests: `app/lab_results/tests/test_config.py` and `app/lab_results/tests/test_batches.py`

What is NOT done yet (still in Phase 4 per roadmap):
- `time_entries.source` and `time_entries.status` columns — no migration yet
- `sample_batches.status` column — no migration yet
- `sample_batches.time_entry_id` must become nullable — no migration yet
- Overlap detection service (`flag_employee_overlaps`)
- Orphan detection service (`orphan_detached_batches`)
- `POST /lab-results/batches/quick-add` endpoint

**The next phase to implement is Phase 3.5 — Audit Infrastructure** (see roadmap). Do that before resuming the remaining Phase 4 items.

---

## Design Decisions Made This Session (Not Yet in Code)

### 1. AuditMixin — apply broadly in one pass

`AuditMixin` (already defined in `app/database/mixins.py` with `created_at`, `updated_at`, `created_by_id`, `updated_by_id`) gets applied to all business entity models. Do this in a single migration, not incrementally — partial coverage makes null values ambiguous ("never set" vs. "set before we wired this in").

**Apply to:** `wa_codes`, `deliverables`, `work_auths`, `work_auth_project_codes`, `work_auth_building_codes`, `rfas`, `rfa_project_codes`, `rfa_building_codes`, `projects`, `employees`, `employee_roles`, `project_deliverables`, `project_building_deliverables`, `time_entries`, `sample_batches`, `sample_types` + all config sub-tables, `schools`, `contractors`, `hygienists`

**Do NOT apply to:** `manager_project_assignments` (already a purpose-built audit trail with `assigned_by`/`assigned_at`/`unassigned_at`), structural M2M association tables (`project_school_links`, `project_contractor_links`, `project_hygienist_links`), auth tables (`users`, `roles`, `permissions`)

### 2. System user sentinel

A reserved `users` row is needed for automated writes:
- Seed it in `app/scripts/db.py` alongside roles/permissions
- Username: `"system"`, no valid password hash, cannot log in
- Define `SYSTEM_USER_ID: int` constant in `app/common/config.py`
- Any service function that writes on behalf of the system passes `user_id=SYSTEM_USER_ID` to set `created_by_id`/`updated_by_id`

### 3. Time entry state model

Two new columns on `time_entries` (need migration + enum definitions in `app/common/enums.py`):

**`source`** — immutable, set at creation:
- `manual` — entered by a manager from activity logs; also set when a manager edits a system-created entry
- `system` — auto-created by quick-add; `created_by_id = SYSTEM_USER_ID`

**`status`** — mutable:
- `assumed` — system placeholder; times are implied (00:00–00:00 next day), not confirmed
- `entered` — manually input or manager-confirmed
- `conflicted` — overlaps another time entry for the same employee on any project; both entries flagged; neither project can close until resolved
- `locked` — project closed; read-only

When a manager edits a `source=system` entry, flip `source → manual`, `status → entered`. `created_by_id` stays as `SYSTEM_USER_ID` — it's the immutable origin. `updated_by_id` = manager's ID.

### 4. Sample batch status

New `status` column on `sample_batches` (need migration + enum in `app/common/enums.py`):
- `active` — normal state
- `orphaned` — `time_entry_id` was deleted or revised; `time_entry_id` becomes `NULL` (the FK must be made nullable); blocks project closure until re-linked or discarded
- `discarded` — explicitly invalidated by manager
- `locked` — project closed; read-only

### 5. Quick-add endpoint design

`POST /lab-results/batches/quick-add` — for managers who have a COC but no pre-existing time entry:
- Accepts `project_id`, `school_id`, `employee_id`, `date_collected` instead of `time_entry_id`
- Calls `resolve_or_create_time_entry()`: finds existing entry for that employee/project/school/date OR creates a placeholder (`source=system`, `status=assumed`, span = `date_collected 00:00 → date_collected+1 00:00`, `created_by_id=SYSTEM_USER_ID`)
- Role resolution: use the first active role matching any `sample_type_required_roles`; if no required roles, use the employee's first active role on `date_collected`; 422 if no active role found
- Inspector resolution: the first `inspector_id` in the list is used as the time entry's `employee_id`

---

## Non-Obvious Technical Patterns Confirmed This Session

### `db.get()` is wrong for GET endpoints that serialize nested relationships

Never use `db.get()` in a route handler that returns an object serialized via a `response_model` containing nested fields. `db.get()` returns the identity-map cached instance and may skip `selectin` loaders, causing `MissingGreenlet` during serialization.

Use this pattern instead in any `get_X_or_404` helper whose result is returned by a GET endpoint:

```python
result = await db.execute(
    select(MyModel)
    .where(MyModel.id == record_id)
    .execution_options(populate_existing=True)
)
obj = result.scalar_one_or_none()
```

`populate_existing=True` forces a re-query even when the object is already in the identity map, ensuring child collections (added after the initial load) are reflected. This is applied to `get_sample_type_or_404` in `app/lab_results/service.py` — apply the same pattern to any future `get_X_or_404` used in GET-by-ID routes with nested response schemas.

### FK validation in service functions that return early

`validate_employee_role_for_sample_type()` in `app/lab_results/service.py` returns early when the sample type has no required roles — it never checks whether the `time_entry_id` actually exists. SQLite does not enforce FK constraints by default, so without an explicit check, a batch with a non-existent `time_entry_id` silently succeeds.

The fix is already in `app/lab_results/router/batches.py`: an explicit `db.get(TimeEntry, body.time_entry_id)` check before the role validation call. Apply this defensive pattern to any future service function that conditionally skips FK existence checks.

---

## Roadmap Changes Made This Session

The roadmap (`backend/data/roadmap.md`) was updated with:
- **Phase 3.5** (new) — Audit Infrastructure; this is the next thing to implement
- **Phase 4** — updated to show completed items (✓) and add the remaining items (time entry state model, quick-add, overlap/orphan detection)
- **Phase 6** — added `lock_project_records()` and conflict/orphan as blocking project flags
- **Design Note — AuditMixin Scope** (new)
- **Design Note — Time Entry and Sample Batch State Model** (new)
- **Follow-up Project — Full Audit Trail** (new deferred section)

Do not start Phase 5 or 6 before Phase 3.5 is complete. AuditMixin is a pre-condition for the full audit trail and for any correct `updated_by_id` tracking in Phase 4's quick-add endpoint.
