# Session Handoff — 2026-04-28

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Phase 6.6 Session C complete** (requirement-types module + namespace cleanup, 2026-04-28). **859 passing** (+19 new tests). Phase 6.6 is now fully complete. No migrations.

Full arc through this phase:

| Session | Summary | Tests |
|---------|---------|-------|
| D | Silo 2 `cprs` | 693 |
| E0a | Module split: `app/common/requirements/` + `app/requirement_triggers/` | 693 |
| E0b + E0b-refactor | Router pattern: project-scoped ops into `app/projects/router/` | 693 |
| E0c | Protocol/schema hygiene (drop `requirement_key`, fix `@computed_field`, add `validate_template_params`, registry coverage test) | 705 |
| E0d | Drop `is_required` columns from cprs + required_docs | 705 |
| E | Silo 3 `dep_filings` | 766 |
| E2 | Silo 4 `lab_reports` — retire `is_report` | 803 |
| F | Closure-gate integration + project status surface | 817 |
| **6.6A** | **FE regen drift — close 409 docs + Deliverables CRUD + cross-side note** | **~825** |
| **6.6B** | **Undismiss symmetry across all four silos + lab_reports parity fix** | **~840** |
| **6.6C** | **Requirement-types module + Literal narrowing + wa-codes remount dropped** | **859** |

**Phase 6.5 is complete. Phase 6.6 is complete.**

---

## Phase 6.6 Session C — What Was Built

### `template_params_model` on each handler

Added `template_params_model: ClassVar[type[BaseModel] | None]` to all five requirement-type handler classes (across six handler registrations):

- `app/required_docs/service.py` — new `ProjectDocumentTemplateParams(BaseModel)` with `extra="forbid"`, field `document_type: DocumentType`. `ProjectDocumentHandler.template_params_model = ProjectDocumentTemplateParams`. `validate_template_params` now delegates to `model_validate(params)` and translates `ValidationError → ValueError`.
- `app/cprs/service.py`, `app/lab_reports/service.py`, `app/dep_filings/service.py`, `app/deliverables/requirement_adapter.py` (both adapters) — `template_params_model = None` (signals "params must be `{}`"). Existing `validate_template_params` bodies unchanged.

Note: `template_params_model` is a handler-class attribute, NOT added to `ProjectRequirement` Protocol (which covers requirement ORM row instances, not handler classes).

### `RequirementTypeName` Literal + registry helpers

- `app/common/requirements/__init__.py` — exports `RequirementTypeName = Literal["project_document", "contractor_payment_record", "lab_report", "project_dep_filing", "deliverable", "building_deliverable"]`.
- `app/common/requirements/registry.py` — added `items() → Iterable[tuple[str, type]]` and `events_for(name) → list[RequirementEvent]` helpers.
- `app/requirement_triggers/schemas.py` — `WACodeRequirementTriggerCreate.requirement_type_name` typed as `RequirementTypeName` (was plain `str`). OpenAPI now emits an enum; Pydantic validates at the schema layer before any service code runs.
- `app/common/requirements/tests/test_registry_coverage.py` — new `test_requirement_type_name_literal_matches_registry` asserts `set(get_args(RequirementTypeName)) == set(registry._handlers.keys())`. Also added missing side-effect imports for `app.dep_filings` and `app.lab_reports`.

### New `app/requirement_types/` module

- `GET /requirement-types` → `list[RequirementTypeInfo]`. One row per registered handler. Fields: `name`, `events` (list of `RequirementEvent` strings), `template_params_schema` (JSON Schema dict — non-empty only for `project_document`), `is_dismissable`, `display_name` (always `None` today; future handlers set via `ClassVar[str]`).
- `app/main.py` — registered `requirement_types_router`.
- 15 new tests in `app/requirement_types/tests/test_router.py`.

### Dropped `/wa-codes/requirement-triggers` re-mount

- `app/wa_codes/router/__init__.py` — removed `router.include_router(requirement_triggers_router)` and its import. Canonical path `/requirement-triggers` unchanged.
- `app/requirement_triggers/README.md` — updated path note.
- 1 regression test in `app/wa_codes/tests/test_router.py`.

---

## Phase 6.6 Session B — What Was Built

### Undismiss endpoints — CPRs, document-requirements, DEP filings

Added `POST /{id}/undismiss` to three routers:
- `app/cprs/router.py` — `POST /cprs/{cpr_id}/undismiss` → `ContractorPaymentRecordRead`; collision check on `(project_id, contractor_id)`
- `app/required_docs/router.py` — `POST /document-requirements/{req_id}/undismiss` → `ProjectDocumentRequirementRead`; collision check on `(project_id, document_type, employee_id, date, school_id)`
- `app/dep_filings/router.py` — `POST /dep-filings/{filing_id}/undismiss` → `ProjectDEPFilingRead`; collision check on `(project_id, dep_filing_form_id)`

All three: 404 if not found, 422 if not dismissed, 409 if a live row already exists for the same key tuple (pre-empts `IntegrityError` 500 from the partial unique index). Requires `PROJECT_EDIT`. Clears `dismissed_at`, `dismissed_by_id`, `dismissal_reason`; sets `updated_by_id`.

### Lab-reports parity fix

Added the same uniqueness pre-check to `app/lab_reports/router.py` undismiss handler (previously missing — would have surfaced as `IntegrityError` 500 on collision). Collision check on `(sample_batch_id)`.

### Tests

4 new tests per silo (undismisses, 422-not-dismissed, 409-collision, 404-unknown) across:
- `app/cprs/tests/test_router.py` — `TestUndismissContractorPaymentRecord`
- `app/required_docs/tests/test_router.py` — `TestUndismissDocumentRequirement`
- `app/dep_filings/tests/test_router_items.py` — `TestUndismissDEPFiling`
- `app/lab_reports/tests/test_router.py` — collision test added to `TestUndismissLabReport`

---

## Phase 6.6 Session A — What Was Built

### 1. `CloseProjectConflictDetail` — 409 shape declared in OpenAPI

New schema `app/projects/schemas.py:CloseProjectConflictDetail` with two optional list fields:
- `blocking_issues: list[BlockingIssue] | None`
- `unfulfilled_requirements: list[UnfulfilledRequirement] | None`

`app/projects/router/base.py` close decorator now has `responses={409: {"model": CloseProjectConflictDetail, ...}}`. No runtime change — the two 409 paths already existed in `lock_project_records`; this just documents them in the OpenAPI schema.

**Design note:** single schema with both keys nullable (not discriminated union) — codebase has no `discriminator=` precedent and the two shapes are key-disjoint. FE narrows on key presence.

### 2. Deliverables CRUD — `POST /deliverables/` + `PATCH /deliverables/{id}`

- `app/deliverables/schemas.py` — new `DeliverableUpdate(name?, description?, level?)`.
- `app/deliverables/router/base.py` — `_ensure_name_unique` helper (422 on collision, mirrors `wa_codes` pattern); `POST /` (201, `created_by_id`); `PATCH /{deliverable_id}` (`exclude_unset=True`, immutable-level 422, name uniqueness excluding self, `updated_by_id`). Both require `PROJECT_EDIT`.
- **Deviation:** ROADMAP said 409 for dup-name; implementation uses **422** to match `employees`/`wa_codes` codebase pattern. ROADMAP updated in passing.
- 7 new tests in `app/deliverables/tests/test_router.py`.

### 3. Frontend cross-side note

`frontend/HANDOFF.md` items 1 and 2 (close 409 schema, Deliverables CRUD) marked resolved. Catalog `Deliverable` field correction noted (only `name`/`description`/`level` — not `internal_status`/`sca_status`).

---

## Next Phase

**Phase 6.6 is complete.** The next major phase is **Phase 6.7 — Peer Dependency Navigation** (see ROADMAP.md §"Phase 6.7"). Work only when a concrete FE consumer asks for a specific lateral edge. The first candidate: `GET /time-entries/{id}/batches`.

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

---

## FE regen drift to address (audit 2026-04-27)

> Captured as **Phase 6.6** in `ROADMAP.md` (Sessions A/B/C). The six items below are the source audit; the ROADMAP entry has the design decisions and session split.

The FE regenerated the OpenAPI client against this branch and audited the result. Most of `frontend/HANDOFF.md`'s pickup list landed cleanly (DEP-filings, lab-reports, document-requirements, CPR endpoints, removed `is_required`/`requirement_key`/`is_report`, all six `*Connections` typed, paginated work-auths, `unfulfilled_requirement_count`, `UnfulfilledRequirement`, `GET /projects/{id}/requirements`). The following items need backend fixes before FE can build cleanly against the contract:

1. **`POST /projects/{id}/close` does not declare its 409 response shape.** `CloseProjectProjectsProjectIdClosePostErrors` in the generated client lists only `422`. The 409 with `{"unfulfilled_requirements": [...]}` or `{"blocking_issues": [...]}` is undocumented in the OpenAPI schema, so the FE has to hand-narrow `unknown` to render the close gate UI. Add `responses={409: ...}` to the route decorator with a discriminated-union model covering both detail shapes.

2. **No standalone Deliverables CRUD endpoints.** `POST /deliverables/` and `PATCH /deliverables/{id}` (with `DeliverableCreate` / `DeliverableUpdate` schemas) are still missing. This blocks Session 2.3e (Deliverables admin). Existing surface: list, single delete, batch import, and trigger management — no single create/update.

3. **`undismiss` is asymmetric across silos.** Only `POST /lab-reports/{id}/undismiss` exists. CPRs, project document requirements, and project DEP filings have no undismiss endpoint. If the four-silo requirements pattern is meant to support reversing a dismissal uniformly, the other three need it.

4. **`WaCodeRequirementTriggerCreate.requirement_type_name` is plain `string`; `template_params` is `dict[str, unknown]`.** Runtime validation in `validate_template_params` rejects unsupported values, but the OpenAPI schema gives the FE no way to discover valid `requirement_type_name` values or per-type `template_params` shape. **Decision (2026-04-27): do both** — (a) type `requirement_type_name` as `Literal[...]` for compile-time narrowing AND (b) expose a new `GET /requirement-types` endpoint (new `app/requirement_types/` module) returning per-type `template_params_schema` (JSON Schema). Each handler gains a `template_params_model: ClassVar[type[BaseModel] | None]` attribute on the Protocol. See ROADMAP.md §Phase 6.6 Session C.

5. **Duplicated requirement-triggers namespace.** SDK has both `createRequirementTriggerRequirementTriggersPost` (`/requirement-triggers`) and `createRequirementTriggerWaCodesRequirementTriggersPost` (`/wa-codes/requirement-triggers`). **Decision (2026-04-27): drop the `/wa-codes/requirement-triggers` re-mount** — remove `router.include_router(requirement_triggers_router)` from `app/wa_codes/router/__init__.py:15`. Canonical path stays `/requirement-triggers/...` (where all existing tests already point). See ROADMAP.md §Phase 6.6 Session C.

6. **Deliverables blocker description in `frontend/HANDOFF.md` is wrong.** It claims the create surface should be "name, description, internal_status, sca_status," but `internal_status` / `sca_status` live on `ProjectDeliverable` / `ProjectBuildingDeliverable`, not the catalog `Deliverable`. The catalog has only `name`, `description`, `level`. Confirm what the Deliverables admin should manage before scoping the create/update payload.
