# Session Handoff — 2026-04-27

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Phase 6.5 Session D complete.** Silo 2 (`cprs`) is fully implemented: model, schemas, service, router, 50 tests, all passing. Full suite: 693 passing.

**Next: Session E — Silo 3: `dep_filing_forms` + `project_dep_filings`.** See ROADMAP.md Phase 6.5 Session E.

---

## What Was Done This Session

### Phase 6.5 Session D — Silo 2: `cprs`

**Files created:**
- `app/cprs/__init__.py` — imports `service` for side-effect registration of `ContractorPaymentRecordHandler`
- `app/cprs/models.py` — `ContractorPaymentRecord` ORM model; inherits `Base, AuditMixin, DismissibleMixin, ManualTerminalMixin`; columns: `project_id`, `contractor_id`, `is_required`, RFA stage (`rfa_submitted_at`, `rfa_internal_status`, `rfa_internal_resolved_at`, `rfa_sca_status`, `rfa_sca_resolved_at`), RFP stage (`rfp_submitted_at`, `rfp_internal_status`, `rfp_internal_resolved_at`, `rfp_saved_at`), `file_id`, `notes`, plus `DismissibleMixin` + `AuditMixin`; partial unique index on `(project_id, contractor_id) WHERE dismissed_at IS NULL`; composite index on `(project_id, rfp_saved_at, dismissed_at)`; `contractor` relationship with `lazy="selectin"`; `is_fulfilled() -> rfp_saved_at IS NOT NULL`
- `app/cprs/schemas.py` — `ContractorPaymentRecordCreate`, `ContractorPaymentRecordUpdate`, `ContractorPaymentRecordDismiss`, `ContractorPaymentRecordRead`; uses `@computed_field` for `label`, `is_fulfilled`, `is_dismissed`
- `app/cprs/service.py` — `materialize_for_contractor_linked`, `cleanup_for_contractor_unlinked` (Decision #6 conditional delete), `record_stage_history_note` (non-blocking history note on re-submission); `ContractorPaymentRecordHandler` registered via `@register_requirement_type("contractor_payment_record", events=[CONTRACTOR_LINKED, CONTRACTOR_UNLINKED])`
- `app/cprs/router.py` — two routers: `projects_cpr_router` (prefix `/projects`) and `cpr_router` (prefix `/contractor-payment-records`); endpoints: list, manual POST (validates contractor link), PATCH (stage regression note on RFA/RFP re-submission), dismiss POST, DELETE (guarded: 422 unless pristine — no RFA/RFP submitted)
- `app/cprs/README.md` — module docs
- `app/cprs/tests/__init__.py`, `test_protocol.py` (13), `test_models.py` (5), `test_dispatch.py` (8), `test_router.py` (20), `test_aggregator.py` (4)

**Files modified:**
- `app/common/enums.py` — added `NoteEntityType.CONTRACTOR_PAYMENT_RECORD`, `NoteType.CPR_STAGE_REGRESSION`, `CPRStageStatus(StrEnum)` (`PENDING`, `APPROVED`, `REJECTED`, `WITHDRAWN`), `RequirementEvent.CONTRACTOR_UNLINKED`
- `app/notes/service.py` — added `ContractorPaymentRecord` to `model_map` in `validate_entity_exists`
- `app/projects/services.py` — added `NoteEntityType.CONTRACTOR_PAYMENT_RECORD` to `_ENTITY_LINK_TEMPLATES`; wired `dispatch_requirement_event` for `CONTRACTOR_LINKED` / `CONTRACTOR_UNLINKED` in `process_project_import` (fires after flush, before commit)
- `app/main.py` — `import app.cprs  # noqa` + `include_router` for both CPR routers
- `backend/ROADMAP.md` — Session D checkbox ticked
- `tests/seeds/__init__.py` — exported `seed_contractor`

### Key decisions locked this session

- **`ManualTerminalMixin` first real consumer (Decision #4):** `ContractorPaymentRecord` is the first silo model to inherit `ManualTerminalMixin`. The mixin adds no columns — it is a marker class setting `has_manual_terminals = True`. The aggregator and future tooling detect it via `getattr(handler_cls, 'has_manual_terminals', False)`.
- **Stage regression notes are non-blocking (divergence from `create_system_note`):** History notes are created directly on the `Note` model with `is_blocking=False, is_resolved=True`. Using `create_system_note` was rejected because it hardcodes `is_blocking=True`. The CPR itself being unfulfilled (via the aggregator) is what gates closure — the regression note is audit trail only.
- **`CONTRACTOR_UNLINKED` event added:** `RequirementEvent.CONTRACTOR_UNLINKED = "contractor_unlinked"` was added to the enum. The dispatch fires from `process_project_import` when the current contractor link is replaced. This is currently the only production source of `CONTRACTOR_UNLINKED`.
- **Decision #6 — conditional de-materialization:** `cleanup_for_contractor_unlinked` deletes a row only if `rfa_submitted_at IS NULL AND dismissed_at IS NULL AND file_id IS NULL`. Progressed rows are kept for manual inspection/dismissal.
- **`label` in `ContractorPaymentRecordRead` schema uses `contractor_id` only (no name):** The Read schema does not have the `contractor` relationship loaded (Pydantic reads from ORM attributes, not relationships during serialization). The label computed_field uses `f"CPR — Contractor #{self.contractor_id}"`. The ORM model's `label` property uses the loaded relationship for richer output when accessed directly.

### Migration needed (user generates)

New table: `contractor_payment_records`

```sql
CREATE TABLE contractor_payment_records (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    contractor_id INTEGER NOT NULL REFERENCES contractors(id) ON DELETE RESTRICT,
    is_required BOOLEAN NOT NULL DEFAULT 1,
    rfa_submitted_at DATETIME,
    rfa_internal_status VARCHAR,  -- 'pending' | 'approved' | 'rejected' | 'withdrawn'
    rfa_internal_resolved_at DATETIME,
    rfa_sca_status VARCHAR,
    rfa_sca_resolved_at DATETIME,
    rfp_submitted_at DATETIME,
    rfp_internal_status VARCHAR,
    rfp_internal_resolved_at DATETIME,
    rfp_saved_at DATETIME,
    file_id INTEGER,
    notes TEXT,
    dismissal_reason TEXT,
    dismissed_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    dismissed_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX ix_contractor_payment_records_project_id
    ON contractor_payment_records (project_id);
CREATE INDEX ix_contractor_payment_records_contractor_id
    ON contractor_payment_records (contractor_id);
CREATE INDEX ix_cpr_status
    ON contractor_payment_records (project_id, rfp_saved_at, dismissed_at);
-- Partial unique index (SQLite 3.8+)
CREATE UNIQUE INDEX ix_uq_cpr_active
    ON contractor_payment_records (project_id, contractor_id)
    WHERE dismissed_at IS NULL;
```

---

## Known gaps / follow-up for Session E or F

1. **`ContractorPaymentRecordRead.label` has no contractor name.** The schema `@computed_field` only has `contractor_id` (Pydantic doesn't load relationships), so it returns `"CPR — Contractor #N"`. The ORM model's `label` property correctly uses `contractor.name` via the `selectin` relationship, but that never reaches the API response. Fix: add `contractor_name: str` to the Read schema, populated from the loaded relationship. Do before Session F when the frontend first consumes this schema.

2. **`process_project_import` is the only production dispatch site for `CONTRACTOR_LINKED` / `CONTRACTOR_UNLINKED`.** No dedicated HTTP endpoint exists to link or unlink a contractor. If one is added in the future (e.g. `PATCH /projects/{id}/contractor`), it must also call `dispatch_requirement_event` for both events.

3. **User-authored blocking notes on CPR entities do not surface in `get_blocking_notes_for_project`.** `NoteEntityType.CONTRACTOR_PAYMENT_RECORD` is registered (the notes endpoint accepts it and `validate_entity_exists` handles it), but `get_blocking_notes_for_project` in `app/projects/services.py` does not walk that entity type. CPR history notes are `is_blocking=False` so this is harmless now, but a manager-authored blocking note on a CPR row would be silently ignored at closure. Session F should add CPR to the `get_blocking_notes_for_project` walk.

---

## Session C carry-over (still pending)

**Migration from Session B still pending (user generates):** `wa_code_requirement_triggers` table — see Session B HANDOFF for exact DDL.

**Migration from Session C still pending (user generates):** `project_document_requirements` table — see Session C HANDOFF for exact DDL.

---

## Frontend cross-side notes

Nothing for FE until Session F. After Session F lands, regen the OpenAPI client — new schemas include `WACodeRequirementTriggerCreate`, `WACodeRequirementTriggerRead`, plus Silo 1–3 schemas.
