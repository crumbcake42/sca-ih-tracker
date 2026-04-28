# dep_filings

## Purpose

Owns Silo 3 of the `ProjectRequirement` framework: DEP filing forms and per-project filing instances.

- `DEPFilingForm` — admin-managed config rows (form code, label, default-selected flag, display order). Adding a new form type requires no migration.
- `ProjectDEPFiling` — one row per `(project, form)` tracking whether the filing has been saved. Satisfies the `ProjectRequirement` protocol.

**Does NOT own:**
- Closure-gate logic (`lock_project_records`) — that is Session F's job. The aggregator picks up unfulfilled `ProjectDEPFiling` rows automatically once this handler is registered.
- File upload infrastructure — `file_id` is nullable; current "saved" state is `is_saved=True` + `saved_at` stamped.

## Non-obvious behavior

**Manager-driven materialization.** Unlike Silos 1–2, `ProjectDEPFiling` rows are created by explicit manager action (`POST /projects/{id}/dep-filings`), not by event dispatch. The handler subscribes to no `RequirementEvent`s (`events=[]`). The registry dispatch loop never calls `handle_event` for this silo.

**Partial unique index.** `ix_uq_dep_filing_active` enforces one live row per `(project_id, dep_filing_form_id)` `WHERE dismissed_at IS NULL`. A dismissed row does not block re-materialization — the manager can re-select a previously dismissed form.

**Idempotent POST.** `POST /projects/{id}/dep-filings` with the same `form_ids` twice produces no duplicate rows. The service skips any `(project, form)` pair that already has a live (non-dismissed) row.

**`saved_at` stamp.** The PATCH endpoint stamps `saved_at` when `is_saved` transitions to `True` and `saved_at` is not yet set. Once set, it is not overwritten.

**Pristine DELETE guard.** `DELETE /dep-filings/{id}` only succeeds for rows where `is_saved=False AND dismissed_at IS NULL AND file_id IS NULL`. Progressed rows must use the dismiss endpoint.

**Guarded form delete.** `DELETE /dep-filings/forms/{id}` is blocked (409) if any `ProjectDEPFiling` references the form, regardless of dismissal state. Uses `create_guarded_delete_router` factory.

**Transaction ownership.** `materialize_for_form_selection` never flushes or commits. The caller (the router `POST /` handler) commits after materialization.

## Router split

Item-level ops (`PATCH /{filing_id}`, `POST /{filing_id}/dismiss`, `DELETE /{filing_id}`) and form admin CRUD (`/dep-filings/forms/*`) live in `app/dep_filings/router.py`.

Project-scoped list/create (`GET /projects/{id}/dep-filings`, `POST /projects/{id}/dep-filings`) live in `app/projects/router/dep_filings.py`.

## Before you modify

- Run `app/dep_filings/tests` before and after changes.
- Handler registration happens via side-effect import in `__init__.py` (`from . import service`). If you rename or move the service, update `__init__.py`.
- The registry coverage test (`app/common/requirements/tests/test_registry_coverage.py`) will fail if `ProjectDEPFiling.requirement_type` stops matching the registered handler name.
- `DEPFilingForm.code` must be unique; the POST and PATCH form endpoints enforce this in the service layer before committing.
