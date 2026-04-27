# Session Handoff — 2026-04-27

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Phase 6.5 Session C complete.** Silo 1 (`project_document_requirements`) is fully implemented: model, schemas, service, router, 50 tests, all passing. Full suite: 643 passing.

**Next: Session D — Silo 2: `contractor_payment_records`.** See ROADMAP.md Phase 6.5 Session D.

---

## What Was Done This Session

### Phase 6.5 Session C — Silo 1: `project_document_requirements`

**Files created:**
- `app/required_docs/__init__.py` — imports `service` for side-effect registration of `ProjectDocumentHandler`
- `app/required_docs/models.py` — `ProjectDocumentRequirement` ORM model; columns: `project_id`, `document_type` (SQLEnum), `is_required`, `is_saved`, `is_placeholder`, `employee_id`, `date`, `school_id`, `file_id`, `expected_role_type`, `wa_code_trigger_id`, `notes`, plus `DismissibleMixin` + `AuditMixin`; partial unique index on `(project_id, document_type, employee_id, date, school_id) WHERE dismissed_at IS NULL`; composite index on `(project_id, is_saved, dismissed_at)`; properties: `requirement_key`, `label`, `is_dismissed`, `is_fulfilled()`
- `app/required_docs/schemas.py` — `ProjectDocumentRequirementCreate`, `ProjectDocumentRequirementUpdate`, `ProjectDocumentRequirementDismiss`, `ProjectDocumentRequirementRead`; uses `@computed_field` for `label`, `is_fulfilled`, `is_dismissed`; uses `from datetime import date as DateField` to avoid Python 3.14 annotation shadowing
- `app/required_docs/service.py` — `ROLES_REQUIRING_DAILY_LOG = {ACM_AIR_TECH: [DAILY_LOG], ACM_PROJECT_MONITOR: [DAILY_LOG]}`; `materialize_for_time_entry`, `materialize_for_wa_code_added`, `cleanup_for_wa_code_removed`; `ProjectDocumentHandler` class registered via `@register_requirement_type("project_document", events=[TIME_ENTRY_CREATED, WA_CODE_ADDED, WA_CODE_REMOVED])`
- `app/required_docs/router.py` — two routers: `projects_doc_router` (prefix `/projects`) and `doc_req_router` (prefix `/document-requirements`); endpoints: list, manual POST, PATCH, dismiss POST, DELETE (guarded: 422 unless `is_placeholder=True AND is_saved=False`)
- `app/required_docs/README.md` — module docs
- `app/required_docs/tests/__init__.py`, `test_protocol.py` (11), `test_models.py` (5), `test_dispatch.py` (13), `test_router.py` (17), `test_aggregator.py` (4)

**Files modified:**
- `app/common/enums.py` — added `DocumentType(StrEnum)` with `DAILY_LOG`, `REOCCUPANCY_LETTER`, `MINOR_LETTER`
- `app/main.py` — `import app.required_docs  # noqa` + `include_router` for both required_docs routers
- `app/time_entries/router.py` — `dispatch_requirement_event(project_id, TIME_ENTRY_CREATED, {time_entry_id: entry.id}, db)` called before `db.commit()` in `create_time_entry`
- `app/lab_results/service.py` — same dispatch call before final commit in `quick_add_batch`
- `backend/ROADMAP.md` — Session C checkbox ticked

### Key decisions locked this session

- **`ProjectDocumentHandler` separate from ORM model (Decision #13):** Handler class lives in `service.py`, not `models.py`. This avoids circular imports: `service.py` imports `ProjectDocumentRequirement` from `models.py`; `models.py` imports nothing from `service.py`. `__init__.py` imports `service` for the side-effect of registering the handler.
- **Silo-owned mapping:** `ROLES_REQUIRING_DAILY_LOG` is a `dict[EmployeeRoleType, list[DocumentType]]` constant in `service.py`. No DB table, no admin CRUD — adding roles is a code change. Chosen because the mapping is tied to the time-entry domain, not to employee role admin.
- **Single `DAILY_LOG` type:** No per-role-kind variants. Drift handling (early end, missing pages, missing license checklists) covered by blocking notes in `app/notes/`.
- **`is_saved` is the only fulfillment signal:** No overlap-check or `EXPECTED` time-entry status in Silo 1.
- **WA code production dispatch pending:** `ProjectDocumentHandler` subscribes to `WA_CODE_ADDED` / `WA_CODE_REMOVED` and the materializers are tested. But the production firing of those events from `app/work_auths/` is deferred to a future session — only `TIME_ENTRY_CREATED` is wired in production today.
- **Decision #6 (conditional de-materialization):** On `WA_CODE_REMOVED`, rows are deleted only if pristine (`is_saved=False AND dismissed_at IS NULL AND file_id IS NULL`). Saved, dismissed, or file-attached rows are kept with `wa_code_trigger_id=NULL` (via ON DELETE SET NULL).
- **`@computed_field` for schema derived fields:** `label`, `is_fulfilled`, `is_dismissed` in `ProjectDocumentRequirementRead` use `@computed_field` + `@property` to avoid Pydantic reading `is_fulfilled` as a bound method instead of a return value.

### Migration needed (user generates)

New table: `project_document_requirements`

```sql
CREATE TABLE project_document_requirements (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    document_type VARCHAR NOT NULL,  -- 'daily_log' | 'reoccupancy_letter' | 'minor_letter'
    is_required BOOLEAN NOT NULL DEFAULT 1,
    is_saved BOOLEAN NOT NULL DEFAULT 0,
    is_placeholder BOOLEAN NOT NULL DEFAULT 0,
    employee_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    date DATE,
    school_id INTEGER REFERENCES schools(id) ON DELETE SET NULL,
    file_id INTEGER,
    expected_role_type VARCHAR,
    wa_code_trigger_id INTEGER REFERENCES wa_code_requirement_triggers(id) ON DELETE SET NULL,
    notes TEXT,
    dismissal_reason TEXT,
    dismissed_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    dismissed_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX ix_project_document_requirements_project_id
    ON project_document_requirements (project_id);
CREATE INDEX ix_project_document_requirements_document_type
    ON project_document_requirements (document_type);
CREATE INDEX ix_project_document_requirements_employee_id
    ON project_document_requirements (employee_id);
CREATE INDEX ix_project_document_requirements_date
    ON project_document_requirements (date);
CREATE INDEX ix_project_document_requirements_school_id
    ON project_document_requirements (school_id);
CREATE INDEX ix_proj_doc_req_status
    ON project_document_requirements (project_id, is_saved, dismissed_at);
-- Partial unique index (SQLite 3.8+)
CREATE UNIQUE INDEX ix_uq_proj_doc_req_active
    ON project_document_requirements (project_id, document_type, employee_id, date, school_id)
    WHERE dismissed_at IS NULL;
```

The alembic migration should use `Index("ix_uq_proj_doc_req_active", ..., unique=True, sqlite_where=text("dismissed_at IS NULL"))`.

---

## Session B carry-over (still pending)

**Migration from Session B still pending (user generates):** `wa_code_requirement_triggers` table — see Session B HANDOFF for exact DDL. This is a prerequisite for the Session C migration (FK dependency: `wa_code_trigger_id` references it).

---

## Frontend cross-side notes

Nothing for FE until Session F. After Session F lands, regen the OpenAPI client — new schemas include `WACodeRequirementTriggerCreate`, `WACodeRequirementTriggerRead`, plus Silo 1–3 schemas.
