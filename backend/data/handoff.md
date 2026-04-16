# Session Handoff — 2026-04-16 (Phase 3.6 Session D complete)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**354 tests passing.** Phase 3.6 is fully complete. All four sessions (data model, service layer, endpoints, integration) are done.

---

## What Was Done This Session

### Phase 3.6 Session D — Integration

- **Added** `_check_no_blocking_notes(deliverable_id, db)` helper to `app/projects/router/deliverables.py` — queries for unresolved, top-level blocking notes on a deliverable entity; raises 422 with a count-aware message if any exist
- **Added** `_BLOCKED_INTERNAL = {InternalDeliverableStatus.IN_REVIEW}` and `_BLOCKED_SCA = {SCADeliverableStatus.UNDER_REVIEW, SCADeliverableStatus.APPROVED}` — the protected status transitions
- **Wired the gate** into both `update_project_deliverable` and `update_building_deliverable` — checked before applying field updates; only fires when the request actually targets a gated status
- **Added** `_seed_blocking_note` helper and 6 new tests to `app/projects/tests/test_deliverables.py`:
  - Blocking note blocks `in_review` (project deliverable)
  - Blocking note does not block non-gated status (project deliverable)
  - Resolved blocking note allows `in_review` (project deliverable)
  - Same three cases for building deliverables (`under_review`, non-gated, `approved`)
- **Updated** `app/notes/README.md` — added Router-level patterns section (route registration order, `expunge`+reload, nested `selectinload`, `populate_existing=True`)
- **Updated** `app/projects/README.md` — added `GET /projects/{id}/blocking-issues` entry
- **Updated** `data/roadmap.md` — Phase 3.6 marked complete; all Session labels marked complete; endpoint checkboxes checked; integration rule updated to reference the actual enum values and both PATCH handlers

---

## Design Decisions Made This Session

### Verified: time-entry conflict system notes are not needed

The roadmap's original plan included `create_system_note` calls on time-entry overlap. This was changed to 422-at-entry-time before Phase 4 was implemented. No service paths were missed — `NoteType.TIME_ENTRY_CONFLICT` exists in the enum but is currently unconnected to any production code path. It is kept in the enum for the day the design decision is revisited, but no wiring is expected.

### Gate fires on the incoming value, not the transition

The blocking-note check fires when `body.internal_status in _BLOCKED_INTERNAL or body.sca_status in _BLOCKED_SCA`. It does not compare against the current row value — so setting a deliverable to `in_review` when it is already `in_review` (e.g., just updating notes) also triggers the check. This is intentional: if the row has a blocking note and someone re-submits the same status, they should still see the 422. The gate is about the target state, not the direction of travel.

---

## Next Step

**Phase 6 — Project Status Engine.** Phase 5 (Observability) is deferred until after Phase 6.

Phase 6 is large. Likely session breakdown:

- **Session A:** `recalculate_deliverable_sca_status(project_id)` service + wire into WA/RFA endpoints
- **Session B:** `ensure_deliverables_exist(project_id)` service + wire into time entry and batch creation
- **Session C:** `derive_project_status(project_id)` + `lock_project_records(project_id)` services
- **Session D:** `GET /projects/{id}/status` and `GET /projects/{id}/blocking-issues` endpoints + status derivation wired into project update endpoints

Check the roadmap for the full task list before starting.
