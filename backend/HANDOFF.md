# Session Handoff — 2026-04-27

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Session F complete** (Closure-gate integration, 2026-04-27). **817 passing** (+14 new tests).

Full arc through this session:

| Session | Summary | Tests |
|---------|---------|-------|
| D | Silo 2 `cprs` | 693 |
| E0a | Module split: `app/common/requirements/` + `app/requirement_triggers/` | 693 |
| E0b + E0b-refactor | Router pattern: project-scoped ops into `app/projects/router/` | 693 |
| E0c | Protocol/schema hygiene (drop `requirement_key`, fix `@computed_field`, add `validate_template_params`, registry coverage test) | 705 |
| E0d | Drop `is_required` columns from cprs + required_docs | 705 |
| E | Silo 3 `dep_filings` | 766 |
| E2 | Silo 4 `lab_reports` — retire `is_report` | 803 |
| **F** | **Closure-gate integration + project status surface** | **817** |

**Phase 6.5 is complete.** All four silos are wired into the closure gate and the aggregator is a live production call.

---

## Session F — What Was Built

### 1. CPR blocking-notes fix (carry-over from E2)

`get_blocking_notes_for_project` (`app/projects/services.py`) previously had no branch for `NoteEntityType.CONTRACTOR_PAYMENT_RECORD`. Added a `cpr_ids_sq` scalar subquery and a 5th `or_()` branch. CPR-attached blocking notes now surface in `derive_project_status`, `lock_project_records`, and `GET /projects/{id}/blocking-issues` automatically.

### 2. Closure gate — aggregator wired into `lock_project_records`

`lock_project_records` now calls `get_unfulfilled_requirements_for_project` after the blocking-notes check. If any unfulfilled requirements exist, raises `HTTPException(409, detail={"unfulfilled_requirements": [...]})`. Blocking notes still take precedence (checked first; if any exist, the unfulfilled check is never reached).

### 3. `ProjectStatusRead` + `derive_project_status`

- New field: `unfulfilled_requirement_count: int` on `ProjectStatusRead` (`app/projects/schemas.py`).
- `derive_project_status` computes it via `get_unfulfilled_requirements_for_project`. Locked-project short-circuit sets it to 0.
- `READY_TO_CLOSE` condition tightened: now requires `unfulfilled_requirement_count == 0` (broader than the previous `outstanding_deliverable_count == 0`, which was already implied — deliverables are included in the aggregator).

### 4. `GET /projects/{id}/requirements`

New project-scoped sub-router at `app/projects/router/requirements.py`. Returns `list[UnfulfilledRequirement]`. Mounted in `app/projects/router/__init__.py` alongside the other silos.

`UnfulfilledRequirement` added to `app/common/requirements/__init__.py` public exports.

---

## Next Phase

Phase 6.5 is done. The next major phase is **Phase 6.7 — Peer Dependency Navigation** (see ROADMAP.md §"Phase 6.7"). Work only when a concrete FE consumer asks for a specific lateral edge. The first candidate: `GET /time-entries/{id}/batches`.

---

## Carry-overs (still valid)

1. **`process_project_import` is the only dispatch site for `CONTRACTOR_LINKED` / `CONTRACTOR_UNLINKED`.** If a dedicated HTTP endpoint is ever added to link/unlink contractors, it must also call `dispatch_requirement_event` for both events.

2. **Manual POST endpoints bypass materializer precondition checks.** `POST /projects/{id}/cprs` and `POST /projects/{id}/document-requirements` accept rows the materializer would reject. Deferred until a concrete bug surfaces.

---

## Migrations still pending (user generates)

- `wa_code_requirement_triggers` (from Session B)
- `project_document_requirements` (from Session C)
- `contractor_payment_records` (from Session D)
- `ALTER TABLE contractor_payment_records DROP COLUMN is_required;` (from Session E0d)
- `ALTER TABLE project_document_requirements DROP COLUMN is_required;` (from Session E0d)
- `dep_filing_forms` + `project_dep_filings` tables (from Session E)
- `ALTER TABLE sample_batches DROP COLUMN is_report;` (from Session E2)
- `lab_report_requirements` table (from Session E2)

No new migrations in Session F.

---

## Frontend cross-side notes

**Regen needed now** (E0d + E + E2 + F all landed). See `frontend/HANDOFF.md` top section for the full change list.

Key FE-impacting changes from Session F:

- `ProjectStatusRead` has new `unfulfilled_requirement_count: int` field.
- New `UnfulfilledRequirement` schema and `GET /projects/{project_id}/requirements` endpoint.
- `POST /projects/{project_id}/close` now 409s with `{"unfulfilled_requirements": [...]}` (in addition to existing `{"blocking_issues": [...]}`). The FE close flow must handle both 409 detail shapes.
