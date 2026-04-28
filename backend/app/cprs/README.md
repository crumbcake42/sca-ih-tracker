# `CPR`s Module

## Purpose

Owns Silo 2 of the Phase 6.5 `ProjectRequirement` protocol: one `ContractorPaymentRecord` row per `(project, contractor)` pair. Tracks whether the contractor's RFA and RFP have been submitted and, ultimately, whether the CPR document has been saved on file (`rfp_saved_at IS NOT NULL`).

**Does NOT own:**

- The contractor or project data (those live in `app/contractors/` and `app/projects/`)
- The link between contractor and project (`ProjectContractorLink` in `app/projects/models/`)
- Generic blocking-note aggregation (that lives in `app/notes/` and `app/projects/services.py`)

## Non-obvious behavior

### Materialization and de-materialization

`ContractorPaymentRecordHandler` is registered in the requirement registry and subscribed to `CONTRACTOR_LINKED` and `CONTRACTOR_UNLINKED` events. These events are dispatched from `app/projects/services.py:process_project_import` when a contractor link is created or dissolved.

The handler class is in `service.py`, separate from the ORM model in `models.py`. This avoids circular imports: `service.py` imports `ContractorPaymentRecord` from `models.py`; `models.py` imports nothing from `service.py`. `__init__.py` imports `service` as a side effect to trigger handler registration.

### Decision #6 — Conditional de-materialization

On `CONTRACTOR_UNLINKED`, `cleanup_for_contractor_unlinked` only deletes a row if it is **pristine**: `rfa_submitted_at IS NULL AND dismissed_at IS NULL AND file_id IS NULL`. Rows with any progression (RFA submitted, dismissed, or a file attached) are left in place for managers to inspect and dismiss.

### Stage regression history notes

When PATCH sets `rfa_submitted_at` or `rfp_submitted_at` and the current value is already non-null (indicating a re-submission), `record_stage_history_note` captures the prior stage values in a system note (`NoteType.CPR_STAGE_REGRESSION`) attached to the CPR entity. The note is `is_blocking=False, is_resolved=True` — it is a history record only and does not gate project closure.

### ManualTerminalMixin

`ContractorPaymentRecord` inherits `ManualTerminalMixin`, which adds the class variable `has_manual_terminals = True`. This signals to the aggregator and future tooling that stage statuses (`rfa_internal_status`, `rfa_sca_status`, `rfp_internal_status`) can reach terminal values that should not be auto-cleared. The mixin adds no columns.

### Partial unique index

`ix_uq_cpr_active` prevents duplicate live CPR rows for the same `(project_id, contractor_id)`. The `WHERE dismissed_at IS NULL` clause allows a new row to be materialized after an existing one is dismissed (e.g., contractor re-linked after being removed).

### Fulfillment signal

`is_fulfilled()` returns `True` iff `rfp_saved_at IS NOT NULL`. SCA's post-save RFP review is intentionally not tracked (per locked decision in ROADMAP.md §6.5).

## Router split

Item-level ops (`PATCH /{cpr_id}`, `POST /{cpr_id}/dismiss`, `DELETE /{cpr_id}`) are in `app/cprs/router.py`. Project-scoped list/create ops (`GET /projects/{project_id}/cprs`, `POST /projects/{project_id}/cprs`) live in `app/projects/router/cprs.py` and are mounted transitively through `projects_router`.

## Before you modify

- Adding a new stage field requires a migration (user-managed) and an update to `ContractorPaymentRecordUpdate` and `ContractorPaymentRecordRead`.
- The `record_stage_history_note` function creates notes directly on the `Note` model (not via `create_system_note`) because history notes are non-blocking. Do not switch to `create_system_note` without verifying the blocking semantics are correct.
- The dispatch wiring in `app/projects/services.py:process_project_import` is currently the only production source of `CONTRACTOR_LINKED` / `CONTRACTOR_UNLINKED` events. If new endpoints for linking/unlinking contractors are added, they must also call `dispatch_requirement_event`.
- `get_blocking_notes_for_project` (Phase 3.6) does NOT walk CPR entity notes — CPR closure gating goes through `get_unfulfilled_requirements_for_project` (the aggregator). Session F integrates the aggregator into `lock_project_records`.
