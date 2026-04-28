# `app/required_docs/` — Project Document Requirements (Silo 1)

## Purpose

Tracks on/off document requirements for a project: `DAILY_LOG`, `REOCCUPANCY_LETTER`, and `MINOR_LETTER`. This is Silo 1 of the `ProjectRequirement` protocol introduced in Phase 6.5.

This module does **not** own: drift detection (log ends a day early, missing pages), file upload infrastructure, or the `ProjectRequirement` protocol itself — those live in `app/notes/` and `app/project_requirements/` respectively.

## Non-obvious behavior

**Single fulfillment signal.** `is_saved=True` is the only thing that marks a row as fulfilled. There is no date-coverage check or page-count validation. Drift problems are expected to be surfaced via user-authored blocking notes through `app/notes/`.

**`ROLES_REQUIRING_DAILY_LOG` is a code constant, not a DB table.** Defined in `service.py`. Adding a new role type requires no migration — edit the dict and redeploy. The two initial values are `ACM_AIR_TECH` and `ACM_PROJECT_MONITOR`.

**`ProjectDocumentHandler` is the registry handler; `ProjectDocumentRequirement` is the ORM model.** The handler is registered via `@register_requirement_type` in `service.py`; `__init__.py` imports `service` as a side effect to trigger registration at startup. The ORM model satisfies the `ProjectRequirement` protocol structurally (its properties match the protocol attrs), but the *dispatch* and *aggregator query* entry points are on the handler class.

**Materialization idempotency.** `materialize_for_time_entry` checks for an existing non-dismissed row matching `(project_id, document_type, employee_id, date, school_id)` before inserting. `materialize_for_wa_code_added` uses `wa_code_trigger_id` as the de-duplication key. Both functions are safe to call multiple times.

**Decision #6 on `WA_CODE_REMOVED`.** `cleanup_for_wa_code_removed` deletes rows that are pristine (`is_saved=False AND dismissed_at IS NULL AND file_id IS NULL`). Progressed rows are left in place — managers must manually dismiss them. This mirrors the `recalculate_deliverable_sca_status` skip-manual-terminals rule.

**Partial unique index.** The index `ix_uq_proj_doc_req_active` is a partial unique index on `(project_id, document_type, employee_id, date, school_id) WHERE dismissed_at IS NULL`. Dismissed rows are excluded, so a row can be re-materialized after dismissal without an integrity error.

**Caller owns the transaction.** None of the `materialize_*` or `cleanup_*` functions call `db.flush()` or `db.commit()`. The router endpoints commit; the dispatch handlers are always called within the router's transaction.

## Router split

Item-level ops (`PATCH /{req_id}`, `POST /{req_id}/dismiss`, `DELETE /{req_id}`) are in `app/required_docs/router.py`. Project-scoped list/create ops (`GET /projects/{project_id}/document-requirements`, `POST /projects/{project_id}/document-requirements`) live in `app/projects/router/required_docs.py` and are mounted transitively through `projects_router`.

## Before you modify

- If you add a new `DocumentType` value: update the `label` property on the model, add a handler branch if the dispatch logic differs, and document what event triggers it.
- If you add a new role type to `ROLES_REQUIRING_DAILY_LOG`: no migration needed, but add a test in `test_dispatch.py` and update this README.
- If `wa_code_requirement_triggers` WA-code-add/remove dispatch gets wired (the WA-code router currently does not call `dispatch_requirement_event` for `WA_CODE_ADDED`/`WA_CODE_REMOVED`), the `WA_CODE_ADDED` and `WA_CODE_REMOVED` handler paths will become active in production. Their tests already exercise them; no code change is needed here.
- Run `.venv/Scripts/python.exe -m pytest app/required_docs/tests -v` after any change.
