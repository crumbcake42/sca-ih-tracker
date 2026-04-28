# Session Handoff — 2026-04-27

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Phase 6.5 Session D complete** (Silo 2 / `cprs`). Full suite: 693 passing.

**Session E0a complete** (module split refactor). `app/project_requirements/` deleted; `app/common/requirements/` + `app/requirement_triggers/` in place; zero `app.project_requirements` references remain. Test count unchanged.

**Session E0b complete** (router pattern refactor). Under-project sub-routers now mount inside `app/projects/router/__init__.py`. URLs unchanged; 693 passing. **Pattern error:** project-scoped routes were left inside child modules — corrected by E0b-refactor (see below). PATTERNS.md entry #17 rewritten to reflect the correct rule.

**Session E0b-refactor complete** (router code move). Project-scoped list/create routes for CPRs and required docs moved out of child modules and into `app/projects/router/cprs.py` + `app/projects/router/required_docs.py`. Child module router files now export item-level ops only. 693 passing.

**Three reviews on 2026-04-27**, no code written:

1. **Path-finalization review** — surfaced module-layering (`app/project_requirements/` mixes contract with specific config) and router-pattern (`/projects` prefix declared from inside child modules) problems. Produced Sessions E0a + E0b. Plan: `../.claude/plans/review-the-current-phase-cached-wilkes.md`.
2. **Architecture evaluation** — confirmed the `ProjectRequirement` abstraction is worth keeping, gutted the speculative Phase 6.7 framework, and surfaced four protocol/schema hygiene items. Produced Sessions E0c + E0d. Plan: `../.claude/plans/confirm-you-have-a-transient-bengio.md`. Comparison doc: `backend/PLANNING-peer-navigation.md`.
3. **Lab-report silo design** — proposed retiring the standalone `SampleBatch.is_report` boolean by modeling the typed lab report as a per-batch `ProjectRequirement` materialized on `BATCH_CREATED`. Produced Session E2 (Silo 4 `lab_reports`). Plan: `../.claude/plans/i-want-to-revisit-refactored-valley.md`.

**Next: E0c → E0d → {E, E2 — independent} → F.** The remaining E0 sub-sessions must each complete with a green test suite before silo work (E and/or E2) starts. Session E (silo 3 `dep_filings`) and Session E2 (silo 4 `lab_reports`) are independent and may land in either order.

> Plans + key memory entries for the E0a–F + E2 arc are checkpointed in `../.claude/{plans,memory}/` so this context travels across machines. See `../.claude/README.md`.

---

## What Was Decided This Session (2026-04-27)

### Part A — Path-finalization review (produced E0a + E0b)

### Problem 1 — `app/project_requirements/` mixes contract layer with specific config

The module currently holds `ProjectRequirement` protocol, `RequirementTypeRegistry`, dispatcher, aggregator, and the dismissibility/manual-terminal mixins (the **contract** that `cprs`, `required_docs`, `deliverables` implement) **alongside** the `WACodeRequirementTrigger` model + its `/requirement-triggers` CRUD router (a specific admin config). The module name no longer reflects what it owns.

**Resolution (Session E0a):**

- `app/common/requirements/` (new) — contract layer: `protocol.py`, `registry.py`, `dispatcher.py` (renamed from `services.py`), `aggregator.py`, `schemas.py` (UnfulfilledRequirement only), README.md, tests/
- `app/requirement_triggers/` (renamed from `app/project_requirements/`) — `models.py`, `schemas.py` (WACodeRequirementTrigger\* only), `services.py` (hash_template_params only), `router.py`, README.md, tests/
- `app/deliverables/requirement_adapter.py` (moved from `app/project_requirements/adapters/deliverables.py`); `app/deliverables/__init__.py` gains side-effect import for handler registration

Decision #11 (in Phase 6.5 Locked Design Decisions) updated to reference `app/requirement_triggers/` instead of `app/project_requirements/`.

### Problem 2 — `app/cprs/router.py` and `app/required_docs/router.py` declare `/projects` URL prefixes from inside the child module

The two-routers-per-file pattern (`projects_cpr_router` + `cpr_router`, etc.) works but has the child reaching into the parent's URL namespace.

**Resolution (Session E0b — Option C):** Each project-scoped child router file exports two `APIRouter` objects:

- An item router with `prefix="/<resource>"` for PATCH/DELETE/dismiss + future Phase-6.7 peer routes
- A no-prefix under-project sub-router whose routes use `/{project_id}/<resource>` paths
- `app/projects/router.py` mounts the under-project sub-routers (its own constructor carries `prefix="/projects"`)
- `main.py` includes only the item routers (and `projects_router`); under-project sub-routers reach the app transitively through `projects_router`
- Mirrors `app/wa_codes/router/__init__.py` mounting `requirement_triggers_router`

URLs are unchanged from today's state.

### Problem 3 — Lateral peer-route endpoint sprawl (deferred to Phase 6.7)

> **Superseded by Part B (architecture evaluation).** The factory framework described below was dropped. See Part B "Decision — defer the peer-route factory; build lateral endpoints by hand." The 12-endpoint estimate collapses to 3–4 once singular FK navigation moves to embedded Read-schema fields. Original Problem 3 text retained below for history.

Lateral peer clusters (e.g. field-work: `lab_result ↔ time_entry ↔ daily_log ↔ wa_code_assignment`) need `GET /<parent>/{id}/<peer>` endpoints. Hand-writing one per pair is 4 × 3 = 12 endpoints just for the field-work cluster. Solution: a `register_peer_query` decorator + `create_peer_routes` factory primitive in `app/common/peer_routes.py` that emits typed routes from declarative edges.

**Resolution (Phase 6.7 — deferred to first consumer):** Design recorded in ROADMAP.md Phase 6.7. Primitive ships as the prerequisite step of the first session that wires a concrete peer endpoint. No infrastructure-without-consumer; no redesign churn (API frozen in ROADMAP).

Constraints frozen for the eventual builder:

1. Lives at `app/common/peer_routes.py`, **not** under `app/common/requirements/` — peer queries work for any project-scoped resource, not just requirements (PLANNING.md §2.2 excluded `SampleBatch` from requirements).
2. Project scoping is enforced inside each query function (not by the framework).
3. Each query returns the **project-scoped form** (e.g. `WorkAuthProjectCode`, not `WACode`).
4. Query functions live in the parent's module; reciprocal imports are read-only at the model level (not circular).
5. The factory call lives in the parent module's router — `<parent>_router.include_router(create_peer_routes(...))`.

### Problem 4 — Admin reviewability of clusters (added to Phase 6.7 scope)

> **Superseded by Part B (architecture evaluation).** The introspection layer described below was dropped. See Part B "Decision — kill Phase 6.7's `requirement_sets/` introspection layer." Replaced by an optional flat `GET /admin/registry-dump`. Original Problem 4 text retained below for history.

The peer-query factory alone makes individual edges typed and consistent, but admins still need to _review_ which clusters exist and _inspect_ what's attached to a given entity without reading source code or READMEs.

**Resolution (Phase 6.7, same session as the framework primitives):** Three read-only endpoints expose the registry to admins. Sets remain developer-defined (no CRUD; no `requirement_sets` table) per Decision #7.

- `register_requirement_set(name, members, description)` added to `app/common/peer_routes.py`
- New `app/requirement_sets/` module — small, owns only router/schemas/tests, no DB tables
- Endpoints:
  - `GET /requirement-sets` — list all registered sets (admin overview)
  - `GET /requirement-sets/{entity_type}` — sets that include this type
  - `GET /requirement-sets/{entity_type}/{entity_id}` — full instantiated cluster state for one entity (typed payload keyed by peer entity_type; response model dynamically constructed per set, similar to `create_guarded_delete_router`'s `{Model.__name__}Connections` pattern)
- Closure state (`is_fulfilled` / `is_dismissed`) surfaces in the by-id payload where peers implement the `ProjectRequirement` protocol; non-requirement peers appear without closure state
- The by-id endpoint is heaviest (N queries per request); intended for admin review and manager-UX "show me everything attached" views, not high-frequency polling — routine reads continue to use individual `GET /<parent>/{id}/<peer>` endpoints

Full spec in ROADMAP.md Phase 6.7 → "Admin-introspection layer".

### Pattern correction (2026-04-27 follow-up session)

**Problem:** PATTERNS.md #17 (written in E0b) documented the CPR export pattern (`cpr_under_project_router` living in `app/cprs/`) as canonical — directly contradicting the manager/hygienist pattern already established in `app/projects/router/`. Any new silo session reading #17 would reproduce the wrong pattern.

**Rule clarified:** URL namespace owns the code. Routes under `/projects/...` belong in `app/projects/router/`. `app/projects/router/__init__.py` must not import from outside `app/projects/`. Project-scoped ops for child modules go in `app/projects/router/<resource>.py`; item-level ops stay in `app/<silo>/router.py`.

**Drawback acknowledged:** modules with both item ops and project-scoped ops now have code split across two directories. Mitigated by a one-liner in each child module's README pointing to `app/projects/router/<resource>.py`.

**Files changed (no code, documentation only):**
- `app/PATTERNS.md` — #17 rewritten
- `HANDOFF.md` — E0b-refactor block added; "Next" sequence updated
- `ROADMAP.md` — router pattern description rewritten; E0b marked complete with error noted; E0b-refactor session added; Session E and E2 router references updated

### Memory entries created (Part A)

- `feedback_module_organization.md` — domain-based organization with strict hierarchy; child modules never declare parent URL prefix
- `feedback_lateral_vs_hierarchical.md` — when to use peer-route factory vs FK + cascade
- `feedback_router_patterns.md` — appended Option C pattern + lateral peer-route pointer

---

### Part B — Architecture evaluation (produced E0c + E0d, gutted Phase 6.7)

Plan reference: `../.claude/plans/confirm-you-have-a-transient-bengio.md`. Comparison doc: `backend/PLANNING-peer-navigation.md`.

**Decision — keep the `ProjectRequirement` abstraction.** Closure-aggregator collapse + `DismissibleMixin` + `WACodeRequirementTrigger` admin config pay for the layer on day one. Going back to bespoke per-silo gates would re-introduce the documentation drift this work was meant to prevent.

**Decision — kill Phase 6.7's `requirement_sets/` introspection layer.** The three endpoints (`GET /requirement-sets`, `/requirement-sets/{type}`, `/requirement-sets/{type}/{id}`) plus `register_requirement_set()` API plus dynamically constructed per-set Pydantic models were developer documentation masquerading as an HTTP surface. Replaced by a single optional `GET /admin/registry-dump` returning flat data (registered types, handler classes, event subscriptions). No `app/requirement_sets/` module.

**Decision — defer the peer-route factory; build lateral endpoints by hand.** The 4×3=12 endpoint estimate for the field-work cluster collapses to 3–4 actually-needed lateral endpoints once singular FK navigation is moved to embedded Read-schema fields. Hand-rolled with descriptive names (`/lab-results/{id}/matching-daily-logs`, not `/lab-results/{id}/daily-logs`) shaped to FE need. Factory extraction trigger: 8+ uniform-shape edges. Constraints frozen in earlier ROADMAP entry carry forward to hand-rolled endpoints. Detail: `PLANNING-peer-navigation.md`.

**Cleanup items produced (Sessions E0c + E0d, before Session E):**

- **E0c.1 — Drop `requirement_key`** from `ProjectRequirement` protocol, `UnfulfilledRequirement` schema, both deliverable adapters. No FE consumer parses it. Pure code.
- **E0c.2 — Remove duplicate `@computed_field`** for `label` and `is_fulfilled` from `ContractorPaymentRecordRead` and `ProjectDocumentRequirementRead`. Source of truth is the model property; `from_attributes=True` carries it through. Confirms the Session-D follow-up about `ContractorPaymentRecordRead.label` missing the contractor name.
- **E0c.3 — Add `validate_template_params(params: dict) -> None`** classmethod to handler protocol. Trigger POST router calls it; bad config (typo'd `document_type`, etc.) returns 422 at config time instead of silently producing no-op rows. Each silo declares its own validator. Also reject triggers whose handler does not subscribe to `WA_CODE_ADDED`.
- **E0c.4 — Registry coverage test** in `app/common/requirements/tests/test_registry_coverage.py`: assert every silo whose model carries a `requirement_type` ClassVar appears in `registry.all_handlers()`.
- **E0d — Drop `is_required` columns** from `contractor_payment_records` and `project_document_requirements`. All materialization paths set this to `True`; no path sets `False`; closure queries filter on it but never see `False`. Vestigial. User-managed migration. Session E builds `dep_filings` without this column.

**Carry-overs / deferred from this evaluation** (do not block Session E):

- **Manual POST endpoints bypass materializer precondition checks.** `POST /projects/{id}/cprs` and `POST /projects/{id}/document-requirements` accept rows the materializer would reject (school not linked to project, employee with no role on date, etc.). Either factor precondition checks out of the materializer and call from both paths, or document the override loudly in each silo's README. Defer until a concrete bug surfaces.
- **`is_dismissable` is class-level on every handler.** Works today because every silo has a single dismissibility policy per type. If per-row dismissibility ever appears (e.g. system-created rows dismissible, manual rows not), the abstraction has no story yet.
- **`dispatch_requirement_event` first-raise abort behaviour** is documented only in the dispatcher docstring. Two silos that both subscribe to `WA_CODE_ADDED` will see a partial dispatch on first error. Worth pinning with a test or one-line comment in each silo's `handle_event`.
- **Trigger `is_active` flag** for "admin disables temporarily without losing existing rows" — not on the roadmap; revisit if a manager asks for it.

### Memory entries to consider after E0c/E0d land

- `feedback_lateral_vs_hierarchical.md` — append the two-layer rule (singular peer → embedded Read schema; lateral peer → bespoke endpoint with descriptive name; debug → `/admin/registry-dump`).
- `app/PATTERNS.md` — new entry codifying the two-layer rule alongside the project-scoped child-router pattern from E0b.

---

### Part C — Lab-report silo design (produced Session E2)

Plan reference: `../.claude/plans/i-want-to-revisit-refactored-valley.md`.

**Problem.** `SampleBatch.is_report` (`app/lab_results/models.py:153`) is a user-toggled boolean indicating whether the typed/printed lab report has arrived to match the field-collected COC. It is set on POST/PATCH/quick-add but is **not** wired into project closure — the design doc says typed reports are required to close, but `lock_project_records` does not validate it. Every other "did this thing get done?" gate is moving into the requirements framework; `is_report` is the last bespoke closure-style flag outside it.

**Decision — model the typed lab report as a per-batch `ProjectRequirement`.** Retire `is_report`. Add a fourth silo `lab_reports` (`app/lab_reports/`) with a `LabReportRequirement` ORM model satisfying the protocol, materialized on `RequirementEvent.BATCH_CREATED` (event already declared in `app/common/enums.py:149`; no new event needed). Closure unification — one source of truth for "what's outstanding" — comes for free once Session F wires the aggregator into `lock_project_records`.

**Locked design choices (2026-04-27 review):**

- **Silo placement**: new top-level module `app/lab_reports/`, not nested under `app/lab_results/`. Mirrors `cprs/` and (incoming) `dep_filings/`. Keeps `ProjectDocumentRequirement`'s identity tuple `(employee, date, school)` clean — lab reports key on `sample_batch_id` instead.
- **Trigger**: hardcoded — every `BATCH_CREATED` materializes one `LabReportRequirement`. No per-sample-type config table from day one. Easy to evolve to configurable later by gating the handler on a config lookup if a sample type ever turns out to be report-free.
- **Migration of `is_report`**: drop the column, no backfill. No production data to preserve.
- **Sequencing**: own session (Session E2), depends only on E0d (uses no-`is_required` shape from day one). Independent of Session E — may land before, after, or alongside it. Closure-gate wiring stays Session F's job; no `lock_project_records` changes in E2.
- **Dismissibility**: yes (`is_dismissable: ClassVar[bool] = True`, `DismissibleMixin`). A manager can dismiss the report requirement on a batch that genuinely doesn't need one. Mirrors `ProjectDocumentRequirement`.

**Carry-overs / deferred from this evaluation** (do not block Session E2):

- **Conditional trigger by sample_type.** If field-only sample types ever appear, gate `materialize_for_batch_created` on a `sample_type_required_reports` config table (mirroring `sample_type_required_roles` / `sample_type_wa_codes`). Not added now — would be premature.
- **File upload wiring.** `LabReportRequirement.file_id` is added nullable per Decision #9 (file upload infrastructure stays deferred); current "saved" state is just `is_saved=True`.

### Memory entries to consider after E2 lands

- Update `feedback_lateral_vs_hierarchical.md` if the bespoke `/lab-reports/{id}/...` endpoints exercise any new edge of the two-layer rule (likely none — they are item ops on the requirement, not peer navigation).

---

## PREREQUISITE — Session E0b-refactor (Router Pattern Fix)

**Must land before E0c.** E0b established the right mounting point (`app/projects/router/__init__.py`) but left project-scoped CPR and required-docs routes defined inside their own child modules — violating the rule that the URL namespace owns the code. PATTERNS.md #17 has been corrected; the code must follow.

**What to move:**

- `app/cprs/router.py`: remove `cpr_under_project_router`; its two routes (`GET /{project_id}/cprs`, `POST /{project_id}/cprs`) move to a new file `app/projects/router/cprs.py` with `router = APIRouter(prefix="/{project_id}/cprs", tags=["CPRs"])`.
- `app/required_docs/router.py`: remove `doc_under_project_router`; its two routes move to `app/projects/router/required_docs.py` with `router = APIRouter(prefix="/{project_id}/document-requirements", tags=["document-requirements"])`.
- `app/projects/router/__init__.py`: remove the two external imports (`from app.cprs.router import cpr_under_project_router`, `from app.required_docs.router import doc_under_project_router`); add imports from the new local files.

Both new `app/projects/router/*.py` files may still import models, schemas, and service functions from `app/cprs/` and `app/required_docs/` — only the router definition moves.

**URLs are unchanged.** Verify with the full test suite green before proceeding to E0c.

Note the split in `app/cprs/README.md` and `app/required_docs/README.md` once done: project-scoped list/create endpoints live in `app/projects/router/cprs.py` / `app/projects/router/required_docs.py`.

---

## Next Session — Session E0c (Protocol & Schema Hygiene)

## Session E0c — Protocol & Schema Hygiene (pure code; no migration)

After E0b lands cleanly. Each bullet below is its own building step per `feedback_session_segmentation.md` — commit and run tests between each.

- **E0c.1** — Drop `requirement_key` from `ProjectRequirement` protocol (`app/common/requirements/protocol.py`), from `UnfulfilledRequirement` schema (`app/common/requirements/schemas.py`), from `DeliverableRequirementAdapter` and `BuildingDeliverableRequirementAdapter` (`app/deliverables/requirement_adapter.py`), and from the model `requirement_key` properties on `ContractorPaymentRecord` and `ProjectDocumentRequirement`. Update tests; OpenAPI schema diff strips one field from `UnfulfilledRequirementRead`.
- **E0c.2** — Remove `@computed_field` `label` and `@computed_field` `is_fulfilled` from `ContractorPaymentRecordRead` (`app/cprs/schemas.py`) and `ProjectDocumentRequirementRead` (`app/required_docs/schemas.py`). Confirm `ConfigDict(from_attributes=True)` carries the model properties through. The CPR `label` will start including the contractor name correctly (closes the Session-D follow-up).
- **E0c.3** — Add `validate_template_params(params: dict) -> None` as a classmethod on each registered handler. `ProjectDocumentHandler` validates `params["document_type"]` against `DocumentType` enum; `ContractorPaymentRecordHandler` accepts only empty dict; deliverable adapters accept only empty dict. Wire into `POST /requirement-triggers` (`app/requirement_triggers/router.py` post-E0a) before persistence — return 422 on validation error. Also reject triggers whose handler does not subscribe to `WA_CODE_ADDED` (404 → 422). Tests cover each.
- **E0c.4** — Registry coverage test in `app/common/requirements/tests/test_registry_coverage.py`. Walk SQLAlchemy `Base.registry.mappers`; for any model carrying a `requirement_type` ClassVar, assert its name is in `registry._handlers`. Catches "added a silo, forgot to register" failure mode.

Verify: full test suite green; OpenAPI client regen produces a small expected diff (FE handoff note).

---

## Then Session E0d — Drop `is_required` columns

After E0c lands cleanly.

- Remove `is_required` Mapped column from `ContractorPaymentRecord` (`app/cprs/models.py`) and `ProjectDocumentRequirement` (`app/required_docs/models.py`).
- Remove `is_required` from Read/Update schemas in both silos.
- Remove `is_required.is_(True)` predicate from `get_unfulfilled_for_project` in both handlers.
- Update materializer functions (`materialize_for_*`) to not set `is_required`.
- User-managed migration: `ALTER TABLE contractor_payment_records DROP COLUMN is_required`; same for `project_document_requirements`.

Verify: full test suite green; OpenAPI diff strips `is_required` from both Read schemas (FE handoff note).

---

## Then Session E — Silo 3: `dep_filings`

Single `app/dep_filings/` module (mirrors `lab_results/` precedent — confirmed in this review session). Lands on the new paths and Option C router pattern from day one. **Does not include `is_required` column** (per E0d outcome). See ROADMAP.md Session E for details.

---

## Carry-over from Session D (still valid)

1. **`ContractorPaymentRecordRead.label` has no contractor name.** Schema computed_field uses `f"CPR — Contractor #{self.contractor_id}"`. Fix before Session F frontend integration: add `contractor_name: str` to the Read schema, populated from the loaded relationship.

2. **`process_project_import` is the only production dispatch site for `CONTRACTOR_LINKED` / `CONTRACTOR_UNLINKED`.** No dedicated HTTP endpoint exists to link/unlink. If one is added (e.g. `PATCH /projects/{id}/contractor`), it must also call `dispatch_requirement_event` for both events.

3. **User-authored blocking notes on CPR entities do not surface in `get_blocking_notes_for_project`.** `NoteEntityType.CONTRACTOR_PAYMENT_RECORD` is registered but the project-level walk does not include it. Session F should add CPR to the walk.

## Migrations still pending (user generates)

- `wa_code_requirement_triggers` (from Session B)
- `project_document_requirements` (from Session C)
- `contractor_payment_records` (from Session D — DDL in prior HANDOFF revision; recover from git history if needed)

Session E0a/E0b/E0c add no new migrations. **Session E0d** adds: drop `is_required` from `contractor_payment_records` and from `project_document_requirements`.

---

## Frontend cross-side notes

Nothing new for FE this session (no code written). Regen points across the upcoming sub-sessions:

- After **E0c** lands: regen the OpenAPI client. `UnfulfilledRequirementRead` loses `requirement_key`. `ContractorPaymentRecordRead` and `ProjectDocumentRequirementRead` `label` / `is_fulfilled` shapes are unchanged in OpenAPI (still computed at serialization, just from the model property now), but the CPR `label` value will start including the contractor name correctly.
- After **E0d** lands: regen again. `ContractorPaymentRecordRead` and `ProjectDocumentRequirementRead` lose `is_required`.
- After **Session E2** lands (independent of E): regen. `SampleBatchRead` / `SampleBatchCreate` / `SampleBatchUpdate` / `SampleBatchQuickAdd` lose `is_report`; new `LabReportRequirementRead` schemas appear; new endpoints `GET /projects/{id}/lab-reports`, `PATCH /lab-reports/{id}/save`, `POST /lab-reports/{id}/dismiss`, `POST /lab-reports/{id}/undismiss`. Frontend that reads or writes `is_report` must move to the new lab-report endpoints.
- After **Session F** lands: final regen — new schemas include `WACodeRequirementTriggerCreate`, `WACodeRequirementTriggerRead`, plus Silo 1–4 schemas (incl. `LabReportRequirement`); `UnfulfilledRequirement` from `app.common.requirements.schemas`.

URLs are stable across the E0a–E0d refactors (verified by OpenAPI diff in each verification step).
