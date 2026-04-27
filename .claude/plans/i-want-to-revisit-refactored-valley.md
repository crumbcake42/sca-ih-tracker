# Fold lab-report tracking into the requirements/triggers pattern

## Context

Today, `SampleBatch.is_report` is a boolean toggled on the batch row when the
typed/printed lab report arrives to match the field-collected COC. It is
user-set on create / PATCH / quick-add and is **not** wired into project
closure — the design doc says typed reports are required to close, but
`lock_project_records` does not validate it (documented Phase 4 gap in
`app/lab_results/README.md`).

Sessions B–D landed a generalized requirements framework that already has
the right hook: `RequirementEvent.BATCH_CREATED` is declared in
`app/common/enums.py:149` but no handler subscribes to it yet. Materialized
requirement rows satisfy `ProjectRequirement` and roll up via
`get_unfulfilled_requirements_for_project()`
(`app/project_requirements/aggregator.py:7`), which iterates every
registered handler — adding a new silo auto-includes its rows in the
unfulfilled list once Session F wires the aggregator into closure.

The change retires the standalone `is_report` boolean and models the typed
lab report as a **dismissible per-batch requirement materialized on
batch creation**. Closure unification (one source of truth for "what's
outstanding") and shape-consistency with the daily-log and wa-code-driven
flows are the goals.

## Decisions locked in

- **Silo placement**: new top-level silo `app/lab_reports/` (mirrors `app/cprs/`
  and the forthcoming `app/dep_filings/` from Session E).
- **Trigger**: hardcoded — every `BATCH_CREATED` materializes one
  `LabReportRequirement` (no per-sample-type config table). Easy to evolve
  to configurable later by gating the handler on a config lookup.
- **Migration of `is_report`**: drop the column, no backfill. No production
  data to preserve.
- **Sequencing**: own session, after Session E0d, before/alongside Session E.
  Closure gating itself stays Session F's job (no `lock_project_records`
  changes here).
- **Dismissibility**: yes, per the existing pattern (`ProjectDocumentRequirement.is_dismissable = True`).
  A manager can dismiss the report requirement on a batch that genuinely
  doesn't need one. Uses `DismissibleMixin` from
  `app/project_requirements/protocol.py:28`.

## Critical files

- `app/lab_results/models.py:136` — `SampleBatch` (drop `is_report`, line 153)
- `app/lab_results/schemas.py` — drop `is_report` from Read/Create/Update/QuickAdd (lines 125, 133, 146, 168)
- `app/lab_results/router/batches.py:63,141,187` — POST/PATCH/quick-add: drop `is_report`, add dispatch
- `app/lab_results/service.py:235` — `quick_add_batch`: drop `is_report` copy, add dispatch
- `app/lab_results/tests/test_batches.py:124,424` — remove `is_report` create/PATCH tests
- `app/lab_results/README.md` — replace the "Phase 4 gap" note with the new pattern
- `app/required_docs/service.py:165` — handler registration template to mimic
- `app/project_requirements/aggregator.py:7` — auto-discovers the new handler; verify
- `app/projects/services.py:535` — `lock_project_records` (no change in this session)
- `ROADMAP.md` — add the new silo to the silo list; cross-reference Session F
- `frontend/HANDOFF.md` — note `is_report` removed from SampleBatch payloads

## New module: `app/lab_reports/`

Files:

- `app/lab_reports/__init__.py`
- `app/lab_reports/models.py` — `LabReportRequirement` ORM model
- `app/lab_reports/service.py` — `LabReportHandler` + `materialize_for_batch_created`
- `app/lab_reports/schemas.py` — `LabReportRequirementRead`, plus mark-saved/dismiss payloads
- `app/lab_reports/router.py` — list / mark-saved / dismiss endpoints (mirror `app/required_docs/router.py`)
- `app/lab_reports/tests/__init__.py`
- `app/lab_reports/tests/test_handler.py`
- `app/lab_reports/tests/test_router.py`
- `app/lab_reports/README.md`

`LabReportRequirement` columns (mirrors `ProjectDocumentRequirement` shape,
keyed on the batch instead of `(employee, date, school)`):

- `id` PK
- `project_id` FK → `projects.id` (CASCADE), index — required for aggregator scoping
- `sample_batch_id` FK → `sample_batches.id` (CASCADE), unique — one row per batch
- `is_saved: bool` (default False) — fulfillment marker (replaces `is_report`)
- `file_id: int | None` — for the eventual upload link
- `notes: str | None`
- `DismissibleMixin` columns (`dismissed_by_id`, `dismissed_at`, `dismissal_reason`)
- `AuditMixin` columns
- Class-level: `requirement_type: ClassVar[str] = "lab_report"`, `is_dismissable: ClassVar[bool] = True`
- `is_fulfilled() -> bool: return self.is_saved`
- `label` property: `f"Lab Report — Batch {batch_num}"` via the `sample_batch` relationship

Unique index: `(sample_batch_id)` with `WHERE dismissed_at IS NULL` (matches
the partial-unique pattern at `app/required_docs/models.py:51`).

## Handler

`LabReportHandler` in `app/lab_reports/service.py`:

- `@register_requirement_type("lab_report", events=[RequirementEvent.BATCH_CREATED])`
- `handle_event(...)` → `await materialize_for_batch_created(project_id, payload["batch_id"], db)`
- `get_unfulfilled_for_project(project_id, db)` returns `LabReportRequirement` rows where
  `is_required` semantics = not saved, not dismissed (no `is_required` column per Session E0d's
  decision to drop that field — fulfillment is `is_saved=False AND dismissed_at IS NULL`).

`materialize_for_batch_created(project_id, batch_id, db)`:

- Look up the `SampleBatch`; if missing or its `time_entry_id` doesn't resolve
  to a project, return.
- Idempotent: skip if a non-dismissed `LabReportRequirement` for this
  `sample_batch_id` already exists.
- Insert `LabReportRequirement(project_id=..., sample_batch_id=..., is_saved=False,
  created_by_id=SYSTEM_USER_ID)`.
- Caller owns the transaction (no flush, no commit).

## Dispatch wiring

Two batch-creation paths must dispatch `BATCH_CREATED`:

1. `app/lab_results/router/batches.py` POST `/batches/` (~line 114) — after
   the batch is added and the `time_entry_id` resolved to a `project_id`,
   call `await dispatch_requirement_event(project_id, RequirementEvent.BATCH_CREATED, {"batch_id": batch.id}, db)`.
   Mirror the placement of the existing `TIME_ENTRY_CREATED` dispatch at
   `app/time_entries/router.py:98`.
2. `app/lab_results/service.py` `quick_add_batch` (~line 253) — already
   dispatches `TIME_ENTRY_CREATED`; add a sibling `BATCH_CREATED` dispatch
   in the same transactional region.

A batch with a null `time_entry_id` cannot resolve to a project today, so
no requirement is materialized. That matches the existing closure rule
that orphaned batches block closure (handled separately in
`lock_project_records`); no change needed here.

## Schema / test removals

- Drop `is_report` from `SampleBatchCreate`, `SampleBatchUpdate`,
  `SampleBatchRead`, `SampleBatchQuickAdd` in `app/lab_results/schemas.py`.
- Drop the column from the model (`app/lab_results/models.py:153`).
- Update existing tests that exercise `is_report` create/PATCH at
  `app/lab_results/tests/test_batches.py:124` and `:424` — the assertions
  shift to "POST `/batches/` creates one `LabReportRequirement` row tied
  to the new batch."
- User generates and applies the migration manually (CLAUDE.md rule: "Never
  run `alembic` commands"). Migration drops `is_report` from `sample_batches`
  and creates the new `lab_report_requirements` table.

## Router endpoints (`app/lab_reports/router.py`)

Mirror `app/required_docs/router.py` shape, scoped by project:

- `GET /projects/{project_id}/lab-reports` — list (filter by `is_saved`, `dismissed_at`)
- `PATCH /lab-reports/{id}/save` — flip `is_saved=True`, set `file_id`
- `POST /lab-reports/{id}/dismiss` — set dismissal columns
- `POST /lab-reports/{id}/undismiss` — clear dismissal columns

Mounted under the project sub-router pattern per
`feedback_module_organization`. No new top-level URL prefix declared from
inside `app/lab_reports/router.py`.

## Tests

- `test_handler.py`: handler registers; `BATCH_CREATED` dispatch creates
  exactly one row; idempotent on duplicate dispatch; respects dismissed
  rows (does not re-create).
- `test_router.py`: list/save/dismiss/undismiss happy paths; permission
  checks; 404s.
- Update `app/lab_results/tests/test_batches.py` so that `POST /batches/`
  asserts a `LabReportRequirement` row was created.
- Aggregator integration: extend an existing `app/project_requirements/tests/`
  test (or add one) that asserts an unsaved `LabReportRequirement` shows
  up in `get_unfulfilled_requirements_for_project(...)`.

Run from `app/`:

```
.venv/Scripts/python.exe -m pytest app/lab_reports/tests app/lab_results/tests app/required_docs/tests app/project_requirements/tests -v
```

## Documentation updates

- `app/lab_reports/README.md` — module purpose; the silo's place in the
  requirements framework; the dispatch contract (caller owns transaction).
- `app/lab_results/README.md` — replace the "Phase 4 `is_report` gap" note
  with a pointer to `app/lab_reports/`.
- `ROADMAP.md` — add Silo 4 (`lab_reports`) to the silo list; note that
  Session F's closure-gate work picks this up automatically.
- `HANDOFF.md` — capture this session's outcome.
- `frontend/HANDOFF.md` — note `is_report` removed from `SampleBatch`
  payloads; new endpoints live under `/projects/{id}/lab-reports` and
  per-row `/lab-reports/{id}/...` (per `feedback_session_scope`, this is
  the only allowed cross-side write).

## Verification

End-to-end manual check:

1. Start backend (`just api`).
2. POST `/batches/` with valid `time_entry_id`. Expected: 201; a
   `LabReportRequirement` row exists with `sample_batch_id=<new id>`,
   `is_saved=False`.
3. `GET /projects/{project_id}/unfulfilled-requirements` (or whatever the
   aggregator exposes today) — confirm the new row appears.
4. PATCH `/lab-reports/{id}/save` — confirm `is_saved=True` and the row
   no longer appears in the unfulfilled list.
5. POST `/lab-reports/{id}/dismiss` on a fresh row — confirm dismissed,
   not in unfulfilled list.
6. Re-dispatch `BATCH_CREATED` (e.g., re-POST equivalent payload) and
   confirm idempotency: still exactly one non-dismissed row per batch.

Tests pass via the pytest invocation above.
