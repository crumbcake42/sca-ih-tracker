# Session Handoff — 2026-04-27

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Session F complete** (Closure-gate integration, 2026-04-27). **817 passing** (+14 new tests). No code was written after Session F — the follow-up session was a pure planning session that designed Phase 6.6 (FE regen drift cleanup) in ROADMAP.md.

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

Phase 6.5 is done. The next phase is **Phase 6.6 — FE Regen Drift Cleanup** (see ROADMAP.md §"Phase 6.6"), addressing the six contract gaps in §"FE regen drift to address" below. Three sessions, no migrations:

- **Session A** — Close 409 docs + Deliverables CRUD + cross-side note (Items 1, 2, 6)
- **Session B** — Undismiss symmetry across cprs/document-requirements/dep-filings + lab_reports parity fix (Item 3)
- **Session C** — `app/requirement_types/` module + Literal narrowing + drop `/wa-codes/requirement-triggers` re-mount (Items 4, 5)

After 6.6, the next major phase is **Phase 6.7 — Peer Dependency Navigation** (see ROADMAP.md §"Phase 6.7"). Work only when a concrete FE consumer asks for a specific lateral edge. The first candidate: `GET /time-entries/{id}/batches`.

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
