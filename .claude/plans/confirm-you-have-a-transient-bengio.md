# Evaluation — `ProjectRequirement` abstraction & Phase 6.5/6.7 UX

## Status (2026-04-27, post-approval)

User accepted all recommendations in this evaluation. ROADMAP.md and
HANDOFF.md were updated in the same session to reflect them:

- **Phase 6.5 unchanged in scope; protocol/schema hygiene added as
  Sessions E0c (pure code) + E0d (drop `is_required` migration)**
  before Session E ships silo 3 (`dep_filings`). E0c covers:
  drop `requirement_key`, remove duplicate `@computed_field` for
  `label`/`is_fulfilled`, add `validate_template_params` to handler
  protocol, registry coverage test.
- **Phase 6.7 framework gutted.** Replaced with a two-layer rule:
  singular peers → embedded Read schema via `selectin`; many-to-many
  lateral → bespoke endpoint with descriptive name; debug →
  `GET /admin/registry-dump`. The peer-route factory and
  `requirement_sets/` introspection module are dropped from the
  roadmap. Comparison doc with use cases + pseudocode:
  `backend/PLANNING-peer-navigation.md`.
- **Cross-cutting concerns logged but deferred** (manual POST
  precondition checks, `is_dismissable` per-row policy,
  `dispatch_requirement_event` first-raise abort docs, trigger
  `is_active` flag) — see HANDOFF.md "Carry-overs / deferred."

Below is the original evaluation as approved.

---

## Context

You asked me to confirm I understand the UX you've proposed for the current
phase of work, illustrate the challenges via concrete use case stories,
evaluate where the planned architecture supports the UX vs. where it
overshoots, and weigh the alternative (abandon the abstraction; go back
to bespoke tables and per-silo gates).

The current phase wraps three closure-gating silos (`cprs`,
`required_docs`, `dep_filings`) under a single `ProjectRequirement`
protocol so the closure aggregator walks **one** registry instead of
N bespoke note sources. Two refactor sub-sessions (E0a module split,
E0b router pattern) are queued before Session E lands silo 3, and a
deferred Phase 6.7 adds a peer-route factory plus three
`/requirement-sets/...` introspection endpoints.

The stated goal: prevent documentation drift, surface bad
configuration, and consolidate management of these requirements.

---

## My read of the UX you're after

A manager working on a project should be able to:

1. **See one outstanding-requirements list.** "These five things must be
   true before this project can close." Whether the row is a CPR, a
   daily log, or a DEP filing is a presentation detail — closure logic
   is uniform.
2. **Drill into each requirement.** Per-row UI is type-specific: a CPR
   row exposes RFA/RFP date fields; a daily log exposes a saved toggle;
   a DEP filing exposes a saved toggle; UI is bespoke per type.
3. **Dismiss with reason** when reality diverges from the schema (e.g.
   contractor never invoiced, so the CPR will never arrive). The
   project keeps closing.
4. **Trust automatic materialization.** Linking a contractor creates
   the CPR row; logging a time entry for an air tech creates the daily
   log row; adding a configured WA code creates whatever requirements
   it triggers. Nothing manual unless the system event was missed.
5. **See bad configuration immediately.** If an admin maps a WA code to
   a non-existent requirement type, or sets template params that don't
   parse, the system tells them at config time.

Closure gate, dismissibility, materialization-from-events, and config
validation are the four UX axes the abstraction is meant to serve.

---

## Hypothetical use case stories

### Story 1 — Closing a project with three silo types active

Manager opens project 73 to close it. Project has:
- An unfulfilled deliverable (`sca_status = pending_wa`)
- Two unfulfilled CPRs (one pristine, one with `rfa_submitted_at` set)
- One missing daily log (Sept 4, school A, employee B)
- One DEP filing not yet saved

Today's gate calls `get_unfulfilled_requirements_for_project(73)`,
walks the four registered handlers, returns five `UnfulfilledRequirement`
rows. Closure UI renders the labels; closure POST returns 409 with the
same payload.

**Architecture supports this cleanly.** This is the strongest argument
for the abstraction (PLANNING.md §1.1).

### Story 2 — Manager dismisses a stuck CPR

The pristine CPR's contractor never invoiced — the work was donated.
Manager hits `POST /cprs/{id}/dismiss` with reason "donated, no invoice
expected." Row stays in DB; aggregator skips it; closure proceeds.

**Architecture supports this cleanly.** `DismissibleMixin` lifts the
columns into one place; per-silo dismiss endpoint is the only piece
that varies.

### Story 3 — Materialization from CONTRACTOR_LINKED event

`process_project_import` adds a contractor to project 73 →
`dispatch_requirement_event(73, CONTRACTOR_LINKED, {contractor_id: 9}, db)`
→ registry finds `ContractorPaymentRecordHandler` subscribed → handler
inserts a pristine CPR row.

**Architecture supports this cleanly.** Per-event subscription via
`register_requirement_type(events=[...])` is small and explicit.

### Story 4 — Admin adds WA code → daily log trigger

Admin POSTs `/requirement-triggers` with
`wa_code_id=42, requirement_type_name="project_document",
template_params={"document_type": "MINOR_LETTER"}`.
Later a user adds WA code 42 to project 73 → dispatch fires
`WA_CODE_ADDED` → `ProjectDocumentHandler.handle_event` calls
`materialize_for_wa_code_added` → row inserted.

**Architecture supports this — but the validation surface is thin.**
See §"Where bad configuration still slips through" below.

### Story 5 — RFA approved, WA code 42 removed by RFA

RFA approval on project 73 removes WA code 42. Dispatch fires
`WA_CODE_REMOVED`. `ProjectDocumentHandler.cleanup_for_wa_code_removed`
runs: pristine rows for that trigger get deleted; rows where
`is_saved=True` or `dismissed_at IS NOT NULL` or `file_id IS NOT NULL`
stay. Manager sees a now-orphaned row; dismisses it manually if the
work is genuinely no longer required.

**Architecture supports this — but `WA_CODE_ADDED` and `WA_CODE_REMOVED`
events are not yet wired** in production WA-code paths
(`required_docs/README.md` notes this). Until they are, this story is
hypothetical. Worth confirming the Session F integration list covers
it.

### Story 6 — Manager opens "everything outstanding" view in the UI

Manager clicks the "outstanding requirements" badge on project 73.
The frontend wants:
- The five rows from Story 1
- Each row rendered with its **type-specific** controls: a CPR row
  shows RFA/RFP date fields and a "submit RFA" button; a daily log
  row shows the saved toggle and an upload slot

`UnfulfilledRequirement` carries `requirement_type`, `requirement_key`,
`label`, dismissibility flags. It does **not** carry the per-type
fields. So the FE renders the unified list (label only, possibly with
an icon by `requirement_type`), and to expose the editable fields the
manager clicks into the row, which loads the per-silo schema via the
silo's own `GET /<resource>/{id}` (PATCH-shape).

This is the right split — but it means the **aggregator's job is
strictly closure-summary**. It is not the FE's main read path for
working with requirements; the per-silo `GET /projects/{id}/<resource>`
endpoints are. See §"Endpoint flexibility vs. what the FE will use."

---

## Architecture evaluation

### Where the architecture genuinely supports the UX

1. **Closure aggregator** — collapses N walks into one. Real readability
   and correctness gain (`get_unfulfilled_requirements_for_project`
   becomes the closure gate's only walk). The protocol is small (six
   attrs + `is_fulfilled()`), so the cost is well-bounded.
2. **`DismissibleMixin`** — three columns lifted out of three silos.
   Mechanical and worth it.
3. **`ManualTerminalMixin`** — marker class is ~3 lines, declares an
   intent that the aggregator and future tooling can respect. Small;
   fine.
4. **Registry as a Python singleton** — the simplest possible
   implementation; side-effect imports populate it; no DB layer for
   the registry itself. Consistent with PATTERNS.md spirit.
5. **`WACodeRequirementTrigger` admin config** — generalizes today's
   `deliverable_wa_code_triggers`. Adding a new trigger is a row insert,
   not a code/migration change. This is the admin-flexibility win.
6. **Module split (E0a/E0b)** — separating the contract layer
   (`app/common/requirements/`) from the specific config
   (`app/requirement_triggers/`) is the right move. The current path
   `app/project_requirements/` does mix layers and the rename earns
   its keep. E0b's two-router-per-file pattern is also the right way
   to mount project-scoped child resources without the child reaching
   into the parent's URL namespace.

### Where the architecture overreaches

#### 1. Phase 6.7 `/requirement-sets/...` introspection endpoints — overengineered

Three new endpoints, dynamically constructed Pydantic models per set
(via `pydantic.create_model`), a `register_requirement_set()` API on
top of the existing type/trigger namespaces, plus a new
`app/requirement_sets/` module. All read-only, all developer-defined.

**The audience inversion is the smell.** Sets are defined in code by
developers (Decision #7), but exposed via "admin overview" endpoints.
The actual purpose is *developer documentation* of "which clusters
exist," not admin self-service — admins cannot configure anything.
Documentation belongs in a README, not in a typed HTTP surface.

The by-id endpoint compounds the problem: it's the heaviest endpoint
in the design (N queries per call), exists to render an admin
"everything attached to this entity" view, and bypasses the
per-resource read endpoints the FE will already be calling.

**Recommendation: drop it.** If a debug surface is needed, expose a
single `GET /admin/registry-dump` returning the registered types,
their event subscriptions, and their handler classes — flat data,
no dynamic models, no per-set framework. Three endpoints with dynamic
Pydantic generation for "admin curiosity" is the textbook
"design for hypothetical future requirements" anti-pattern this CLAUDE.md
explicitly calls out.

#### 2. Phase 6.7 peer-route factory — defer until two clusters need it

The 4 × 3 = 12 endpoint estimate for the field-work cluster is real,
but only if you actually want all 12 endpoints. In practice:

- `lab_result → time_entry` is "the one time entry that owns this
  batch" (singular, already a FK on the row — solved by enriching the
  Read schema, no peer endpoint needed).
- `lab_result → daily_log` is "all daily logs for this batch's
  (project, employee, date)" — yes, this is a real lateral query.
- `time_entry → lab_result` is "all batches for this entry" — real.
- `wa_code_assignment → time_entry` is "all time entries billed to
  this code" — real, but heavy enough that you may actually want a
  paginated endpoint with filters, not a generic factory output.

Most of the 12 collapse into either (a) a field on the existing Read
schema with `selectin` eager loading or (b) a small number of bespoke
endpoints with the right shape (paginated, filtered, the right join
already encoded). Hand-rolling 3–4 lateral endpoints with descriptive
names is faster than building the factory + decorator + dynamic
response-model wiring.

**Recommendation: build the field-work cluster's lateral endpoints by
hand. Revisit the factory only if a second cluster appears with the
same N×N shape.** The framework constraints you've already frozen in
ROADMAP.md are correct — they will still hold whenever you do build it.

#### 3. `is_required` column on every silo — vestigial

`ContractorPaymentRecord.is_required`,
`ProjectDocumentRequirement.is_required`, planned
`ProjectDEPFiling.is_required` — all default to `True`, all
materialization paths set them to `True`, no path sets them to
`False`. They show up in Read schemas and Update schemas as if they
do something. The closure query already filters
`is_required.is_(True)` and the column has never blocked anything.

Either define the UX flow that toggles `is_required=False` (and what
that means semantically — distinct from "dismissed"?), or drop the
column. Right now it's silent dead weight.

#### 4. `requirement_key` on the protocol — has no consumer

The aggregator returns it, the README explicitly says "per-type
endpoints introduced in Session F will parse them," and no FE code
touches it. For deliverables it's `str(deliverable_id)`; for building
deliverables it's `f"{deliverable_id}:{school_id}"`; for documents
it's a 4-segment composite. If the FE never navigates by it,
`requirement_key` is overhead in the protocol and overhead in the
schema. The label + `requirement_type` is enough to render the row;
clicking into the row goes to a per-silo endpoint that uses the
silo's own primary key.

**Recommendation: drop `requirement_key` from `ProjectRequirement` and
from `UnfulfilledRequirement`.** Add it back only when a concrete FE
consumer needs it. The aggregator already de-duplicates per silo; the
key isn't load-bearing.

#### 5. Three independent materialization-trigger registration surfaces — drift risk

There are three places the system declares "what triggers a requirement":
1. **`wa_code_requirement_triggers` table rows** (admin config) —
   forward materialization on `WA_CODE_ADDED`.
2. **`@register_requirement_type(events=[...])`** decorator (code) —
   which events the handler subscribes to.
3. **In-code mappings** like `ROLES_REQUIRING_DAILY_LOG` in
   `required_docs/service.py` — `TIME_ENTRY_CREATED → DAILY_LOG` for
   specific roles.

These three surfaces can disagree silently:
- Admin POSTs a trigger row for type "project_document" but the
  registered handler doesn't subscribe to `WA_CODE_ADDED` → row
  exists, never fires. (Today: trigger router validates the type
  exists in the registry, but **does not validate the handler
  subscribes to the relevant event**.)
- Admin POSTs `template_params={"document_type": "DAILT_LOG"}` (typo)
  → row created, materialization sees `ValueError` on `DocumentType()`,
  silently `continue`s. Trigger sits in the DB doing nothing forever.
  No 422 at config time.
- Adding a new role to `ROLES_REQUIRING_DAILY_LOG` is a code change
  that's invisible to admins reading `wa_code_requirement_triggers`;
  the admin sees the trigger config but not the role-driven path.

This is exactly the documentation-drift / bad-configuration surface
you said this work is supposed to prevent.

**Recommendation: add a `validate_template_params(params: dict) → None`
method to the handler protocol.** The trigger POST router calls it
before persisting. Each silo declares what shape of params it
accepts (e.g. `ProjectDocumentHandler.validate_template_params`
checks `document_type` is a valid `DocumentType` enum value). Bad
configuration becomes a 422 at config time, not a silent no-op
forever.

Also consider adding to the trigger POST router:
```
if event_required(handler) not in handler.subscribed_events:
    raise 422("requirement type does not subscribe to WA_CODE_ADDED")
```

#### 6. Two computed-field paths for `label` and `is_fulfilled` — drift risk

`ContractorPaymentRecord.label` (model property) and
`ContractorPaymentRecordRead.label` (`@computed_field`) both define
the same string. The Read schema's version says
`f"CPR — Contractor #{self.contractor_id}"` (no name); the model's
version is `f"CPR — {self.contractor.name}"` when the relationship
is loaded. Same `is_fulfilled`. HANDOFF.md notes this as a Session F
TODO.

This is the documentation-drift you want to stop. The protocol expects
`label` on the row — that's the source of truth. Read schemas should
**not** redefine label; let `from_attributes=True` pull the property
through. The current double-definition is what's already producing
the wrong answer in the Read schema.

**Recommendation: remove `@computed_field` `label` and `is_fulfilled`
from the silo Read schemas.** Confirm `from_attributes=True` carries
the model properties through. One source of truth, not two.

---

## Edge cases / overlooked consequences

1. **Manual POST endpoints can create rows that bypass materialization
   logic.** `POST /projects/{id}/cprs` and
   `POST /projects/{id}/document-requirements` exist for "admin
   correction or missed event." But they do not validate that the
   resulting row is one the system *would* have materialized. A manager
   can create a daily-log row for a school not linked to the project,
   for an employee with no role at that date, etc. The materialization
   functions check those preconditions; the manual endpoints don't.
   Either: (a) accept this as an "admin override" and document it
   loudly in the README, or (b) factor the precondition checks out of
   the materializer and call them from both paths.

2. **No coverage for the "admin disables a trigger" UX.** Today the
   only trigger lifecycle is POST/DELETE. If an admin wants to
   temporarily stop materializing a requirement type from a WA code
   without losing the existing rows, they have to delete the trigger
   (and accept that the WA-code-removal cleanup logic will run). A
   nullable `is_active` flag on `wa_code_requirement_triggers` would
   solve this, but it's not on the roadmap. Worth deciding whether
   "admin reversibility" is a real requirement before Session E lands.

3. **`is_dismissable` is class-level on every handler, but the
   protocol exposes it as an instance attribute.** This works because
   every silo today has a single dismissibility policy per type.
   `BuildingDeliverableRequirementAdapter.is_dismissable = False`
   reflects that deliverables aren't dismissible. If a silo ever wants
   per-row dismissibility (e.g. "system-created CPRs are dismissible,
   manual ones are not"), the abstraction has no story. Today it
   doesn't matter; flagging it as a foreseeable next pressure.

4. **`get_blocking_notes_for_project` and
   `get_unfulfilled_requirements_for_project` are independently
   walking the project, called in tandem from `lock_project_records`
   and `derive_project_status`.** They will diverge in coverage if
   someone adds a new silo and forgets to register a handler. The
   only safety net is the equivalence-gate test (deliverable count
   match). Worth adding a "registry coverage" test that asserts every
   silo with a `requirement_type` ClassVar appears in
   `registry.all_handlers()`.

5. **The `cprs` and `required_docs` routers each declare two
   `APIRouter` objects in one file with `/projects` prefix.** Session
   E0b fixes this. But until E0b lands, child modules are still
   reaching into the parent namespace, which violates
   `feedback_module_organization.md`. E0a + E0b should genuinely run
   before Session E — order matters.

6. **The `dispatch_requirement_event` first-raise abort** ("First
   raising handler aborts the dispatch") could surprise a future
   maintainer adding a new handler. If two silos subscribe to
   `WA_CODE_ADDED` and the first throws, the second never runs. That's
   intentional (caller owns the transaction; partial dispatch is
   wrong) — but the docstring is the only place that says so. Worth
   either a test that pins this behaviour or a one-line comment in
   each silo's `handle_event` explaining the contract.

---

## Endpoint flexibility vs. what the FE will reasonably use

Inventory of endpoints introduced or planned by this phase:

| Endpoint | Audience | FE will use? |
|---|---|---|
| `GET /projects/{id}/cprs` | Manager (project page) | Yes — primary read path for the CPR table |
| `POST /projects/{id}/cprs` | Manager (rare correction) | Yes — but rare |
| `PATCH /cprs/{id}` | Manager | Yes — RFA/RFP date entry |
| `POST /cprs/{id}/dismiss` | Manager | Yes |
| `DELETE /cprs/{id}` | Manager | Yes — pristine-only |
| Same set for `/document-requirements` | Manager | Yes |
| Same set for `/dep-filings` (planned) | Manager | Yes |
| `POST/GET/DELETE /requirement-triggers` | Admin | Yes — low frequency |
| `GET /projects/{id}/requirements` (Session F) | Manager (closure UI badge / dialog) | Yes — for label + count + dismiss flag |
| `GET /requirement-sets` (Phase 6.7) | Admin curiosity | **No concrete use** |
| `GET /requirement-sets/{type}` (Phase 6.7) | Admin curiosity | **No concrete use** |
| `GET /requirement-sets/{type}/{id}` (Phase 6.7) | Admin / "everything attached" | **Speculative** |
| `GET /<parent>/{id}/<peer>` × 12 (Phase 6.7) | Lateral nav | **2–4 of 12 will be used** |

The first three groups are clearly justified. The last two are open-
ended speculation about navigation patterns the FE has not yet
asked for.

**Frontend reality check:** the FE's `types.gen.ts` will eat
everything in OpenAPI. Twelve generated `useGetLabResultsByIdDailyLogs`
hooks plus three `useGetRequirementSets...` hooks plus the dynamically
generated per-set response types is real surface area for the FE side
to ignore — and "ignore" usually rots into "use the wrong one." Less
is more here.

---

## Tradeoff: keep, abandon, or reshape?

### Argument for abandoning the abstraction (back to bespoke tables/types)

- The schema is anyway three separate tables with bespoke columns. The
  protocol layer doesn't reduce per-silo code volume — it adds it
  (registry, dispatcher, aggregator, mixins, README).
- Each silo's `compute_is_fulfilled` is bespoke; the abstraction
  doesn't generalize the *interesting* logic.
- Closure logic without the abstraction is three `get_unfulfilled_X`
  helpers and three `extend()` calls in `lock_project_records`. That's
  ≈30 LOC of "duplication."

### Argument for keeping it

- The closure-gate consolidation in `lock_project_records` and
  `derive_project_status` is the only place where adding a 4th silo
  needs to be invisible. Today: register a handler, the gate
  automatically picks it up. Without the abstraction: edit the
  closure walk, edit the project status schema, edit the
  outstanding-count derivation. That's exactly the "documentation
  drift" you cited as the work's reason for being.
- The `WACodeRequirementTrigger` admin config table only earns its
  keep when `requirement_type_name` is polymorphic. Without the
  protocol, that table either splits into N per-silo trigger tables
  or stays as a magic string indexed against per-silo handlers — the
  latter is the abstraction with worse boundaries.
- The **mixins** (`DismissibleMixin`, `ManualTerminalMixin`) are
  worth it independently: lifting `(dismissal_reason,
  dismissed_by_id, dismissed_at)` into one declaration replaces three
  near-identical column triplets.

**My recommendation: keep the abstraction; the closure-gate and
mixin gains pay for it on day one. Cut the speculative add-ons that
overshoot the actual UX.**

### What to keep (high confidence)

- `ProjectRequirement` protocol (with `requirement_key` removed)
- `RequirementTypeRegistry` + `register_requirement_type` decorator
- `dispatch_requirement_event` (forward-only as today)
- `get_unfulfilled_requirements_for_project` aggregator
- `DismissibleMixin`, `ManualTerminalMixin`
- `WACodeRequirementTrigger` admin config
- E0a module split (contract → `app/common/requirements/`,
  trigger → `app/requirement_triggers/`)
- E0b router pattern (item router + under-project sub-router)
- Per-silo bespoke routes for read/list/create/update/dismiss/delete

### What to cut or defer

1. **Phase 6.7 `requirement_sets` introspection endpoints** — drop
   entirely or replace with a single `/admin/registry-dump` debug
   endpoint that returns flat data (no dynamic Pydantic models, no
   `register_requirement_set` API).
2. **Peer-route factory** — defer until a second cluster appears with
   the same N×N shape. Build the field-work cluster's lateral
   endpoints by hand (3–4 of them; not 12). Most "peers" are better
   served by enriching the parent's Read schema with `selectin`-loaded
   related rows.
3. **`requirement_key`** — remove from the protocol and from
   `UnfulfilledRequirement`. Add back only when a concrete FE
   consumer requires it.
4. **`is_required` column on every silo** — drop or define the UX
   flow that toggles it to `False`.

### What to tighten before Session E

1. **Trigger config validation** — add
   `validate_template_params(params: dict) → None` to the handler
   protocol; call it from `POST /requirement-triggers`. Bad config
   becomes 422 at config time. Also reject triggers whose
   `requirement_type_name` doesn't subscribe to `WA_CODE_ADDED`.
2. **One source of truth for `label` and `is_fulfilled`** — remove
   the duplicate `@computed_field` definitions from silo Read
   schemas; rely on `from_attributes=True` to pull the model
   properties through.
3. **Registry coverage test** — assert every silo whose model
   declares a `requirement_type` ClassVar is registered as a handler.
   Catches the "added a silo, forgot to register" failure mode.
4. **Manual POST endpoints** — either factor the materializer's
   precondition checks into reusable helpers and call them from
   both the materializer and the manual POST, or document loudly
   that manual POST is an admin override that bypasses the checks.

---

## A better option for "peer dependency sets"?

You asked. Yes, with caveats:

The problem isn't really "we have peer sets that need framework-level
typing." It's "we have one closure axis (uniform) plus N navigational
axes (bespoke)." Conflating those into one framework forces the
navigational axes to be uniform too, which they aren't.

Two-layer answer that scales better than the peer-route factory:

1. **Closure axis: the abstraction already nails this.** The
   `get_unfulfilled_requirements_for_project` aggregator with the
   minimal `ProjectRequirement` protocol. Don't add to it.
2. **Navigational axis: enrich Read schemas, not add endpoints.**
   Most lateral peers are already discoverable from the row itself
   via FK columns. Use SQLAlchemy `selectin` to eager-load and
   include the peer summary in the Read schema. The FE renders
   hyperlinks from those embedded peers; no `GET /<parent>/{id}/<peer>`
   round-trip needed.
   Example: `ContractorPaymentRecordRead` could include
   `triggering_wa_codes: list[WaCodeMini]` if relevant; the FE
   renders them as links to the WA-code page. No factory, no
   registry, no dynamic Pydantic.
3. **Genuine many-to-many lateral navigation** (e.g. "all batches for
   this time entry") — these become a small number of bespoke,
   paginated, filterable endpoints with descriptive names. Not 12 of
   them. 3–4. Each one ships when the FE asks for it. If the count
   ever passes ~8 of them with the same shape, *then* extract a
   factory — the constraints you've frozen in ROADMAP.md will still
   hold.

This avoids the "build infrastructure-without-consumer" trap and
keeps the OpenAPI surface honest about what the FE actually uses.

---

## Critical files referenced

- `backend/app/project_requirements/protocol.py` — protocol + mixins
- `backend/app/project_requirements/registry.py` — registry singleton
- `backend/app/project_requirements/services.py` — dispatcher
- `backend/app/project_requirements/aggregator.py` — closure walk
- `backend/app/project_requirements/router.py` — trigger CRUD
- `backend/app/project_requirements/adapters/deliverables.py` —
  deliverable adapter
- `backend/app/cprs/{models,service,router,schemas}.py` — silo 2
- `backend/app/required_docs/{models,service,router,schemas}.py` —
  silo 1
- `backend/PLANNING.md` — original abstraction evaluation
- `backend/ROADMAP.md` Phase 6.5 / 6.7 / Sessions E0a–F
- `backend/HANDOFF.md` — current session state

---

## Verification (if you act on the recommendations)

This document is an evaluation; the recommendations split into
several discrete sessions of their own. Each is small enough that
the existing Session E0a/E0b plans can absorb the directionally
aligned ones (drop `requirement_key`, drop `is_required`, remove
duplicate computed_fields) without expanding scope. The bigger
shapes (cut Phase 6.7 introspection, defer peer-route factory) are
roadmap edits, not code changes — they happen by deletion in
ROADMAP.md when you're ready to commit.

If you want, the next concrete step would be a separate planning
session that picks one of these and writes the actual implementation
plan. Don't bundle them — each one is its own building step per
`feedback_session_segmentation.md`.
