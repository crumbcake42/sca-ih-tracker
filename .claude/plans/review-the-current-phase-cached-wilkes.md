# Phase 6.5 — Path Finalization, Requirements Refactor, and Lateral Peer-Route Framework

## Context

Phase 6.5 is mid-flight: Sessions A–D shipped (protocol/registry, trigger
config, document-requirements silo, CPR silo), Sessions E (dep_filings) and
F (closure-gate integration) still pending. While reviewing the work
already landed, three organization problems surfaced:

1. **`app/project_requirements/` mixes a contract layer with a specific
   trigger config.** It currently holds the `ProjectRequirement` protocol,
   `RequirementTypeRegistry`, dispatcher, aggregator, and `Dismissible`/
   `ManualTerminal` mixins (the **contract** that `cprs`, `required_docs`,
   `deliverables` implement) **alongside** the `WACodeRequirementTrigger`
   model + its `/requirement-triggers` CRUD router (a specific admin
   config). The module name no longer reflects what it owns; downstream
   modules import primitives from a path whose name suggests "everything
   project-requirement-related lives here," which obscures the hierarchy
   contract → implementations.

2. **`app/cprs/router.py` and `app/required_docs/router.py` declare a
   `/projects` URL prefix from inside the child resource's module.** The
   "two routers per file" pattern (`projects_cpr_router` + `cpr_router`,
   `projects_doc_router` + `doc_req_router`) works, but it has the child
   module reaching into the parent's URL namespace, and Sessions E/F will
   replicate this pattern for two more silos plus a project-level
   requirements aggregator endpoint if not addressed first.

3. **The codebase has lateral peer clusters that will explode endpoint
   counts if handled per-pair.** Several entities form clusters where any
   peer can be the entry point and a manager wants to navigate to any
   other peer scoped to the parent's project. The user's example —
   field-work cluster: `lab_result ↔ time_entry ↔ daily_log ↔
wa_code_assignment` — is 4 entities × 3 peers per entity = 12
   read-side endpoints, plus the create-side materialization paths. With
   no shared mechanism, each pair becomes a hand-written endpoint and
   each entity's router grows linearly with the cluster size. The need
   is real (managers expect `GET /lab-results/{batch_id}/daily-logs` etc.
   to "just work"), but per-pair endpoints will not scale and will
   diverge over time.

   Crucially, peer responses must return the **project-scoped form** of
   the peer, not the global primitive — e.g. `lab-results/{id}/wa-codes`
   returns `WorkAuthProjectCode` / `WorkAuthBuildingCode` rows (the
   in-project link), not bare `WACode` rows.

   This problem is **distinct from hierarchical ownership** (e.g.
   `sample_type` → `sample_subtype`, where the parent owns the children
   via FK and cascade). Hierarchical relationships have a single owner
   and a clear ownership lifecycle; lateral clusters have no owner —
   peers are allied, not owned, and orphaning behaviour is per-edge.
   These two patterns must stay distinct in code; they should not share
   the same primitive.

Now is the moment to fix problems 1 and 2: Session D has just landed, the
next two sessions will quadruple the cost of fixing later (3 silos × the
trigger module × the deliverables adapter × Session F's new aggregator
endpoint), and no migrations need to change — this is pure code
reorganization plus import updates. Problem 3 (the lateral peer
framework) is **designed in this plan and documented in ROADMAP.md, but
its primitives ship in a later session driven by the first concrete peer
endpoint** (likely Session E or a dedicated framework session) to avoid
building infrastructure with no consumer.

The user's two principles (encoded into memory below):

- **Domain-based module organization with strict hierarchy.**
  Shared/contract primitives belong under `app/common/`; domain-specific
  config and routes belong in their own named module whose name matches
  what it owns. Cross-module imports must reflect a strict hierarchy —
  contract layer imports nothing from concrete implementations;
  implementations import only from the contract layer plus their own
  dependencies.
- **Lateral peer clusters use a peer-route factory; hierarchical
  ownership uses FK + cascade.** Do not unify the two. Lateral peer
  endpoints (`/<parent>/{id}/<peer>`) are factory-generated from
  declarative edges so cluster size does not drive endpoint sprawl.
  Hierarchical relationships continue to use FK ownership, cascade, and
  the existing guarded-delete factory.

---

## Refactor 1 — Split `app/project_requirements/` into two modules

### Target structure

```
app/common/requirements/                  (NEW — the contract layer)
├── __init__.py
├── README.md                             (moved + scoped to contract only)
├── protocol.py                           (moved as-is)
├── registry.py                           (moved as-is)
├── dispatcher.py                         (renamed from services.py)
├── aggregator.py                         (moved as-is)
├── schemas.py                            (UnfulfilledRequirement only)
└── tests/
    ├── __init__.py
    ├── test_protocol.py                  (moved)
    ├── test_dispatch.py                  (moved)
    └── test_aggregator.py                (moved)

app/requirement_triggers/                 (RENAMED from project_requirements)
├── __init__.py
├── README.md                             (rewritten — scope is triggers only)
├── models.py                             (WACodeRequirementTrigger)
├── schemas.py                            (WACodeRequirementTriggerCreate/Read)
├── services.py                           (hash_template_params only)
├── router.py                             (/requirement-triggers CRUD)
└── tests/
    ├── __init__.py
    ├── test_models.py                    (moved)
    ├── test_router.py                    (moved)
    └── test_hash.py                      (moved)

app/deliverables/                         (gains the read-only adapter)
├── ... (existing files unchanged)
├── requirement_adapter.py                (moved from project_requirements/adapters/deliverables.py)
└── tests/
    └── test_requirement_adapter.py       (renamed/moved from project_requirements/tests if any covers adapter)
```

The old `app/project_requirements/` directory and its `adapters/` subfolder
are **removed entirely** after the move.

### Why each file lands where it does

- **`protocol.py`, `registry.py`, `dispatcher.py`, `aggregator.py`,
  `schemas.py` (UnfulfilledRequirement)** are pure contract — they define
  _what_ a requirement type must look like, _how_ events are routed, and
  _how_ the closure gate aggregates. They couple only to
  `app.common.enums.RequirementEvent` (already in common) and SQLAlchemy
  primitives. They are exactly the kind of cross-cutting infrastructure
  that belongs alongside `app/common/factories/`, `app/common/guards.py`,
  `app/common/crud.py`.
- **`services.py` → `dispatcher.py`** because the file's only function is
  `dispatch_requirement_event`. The rename matches what the file does
  (`hash_template_params` moves out — see below). Generic `services.py`
  in a contract module is misleading.
- **`hash_template_params`** belongs with the trigger module, not the
  contract layer — it hashes the trigger's `template_params` dict for
  uniqueness deduplication. It has no role in the protocol or registry.
- **`WACodeRequirementTrigger` model + schemas + router** stay together
  in `app/requirement_triggers/`. The module name now matches the model
  and route prefix exactly (`/requirement-triggers`).
- **`adapters/deliverables.py` → `app/deliverables/requirement_adapter.py`**
  because the adapter wraps `ProjectDeliverable` rows. The thing being
  adapted is owned by `deliverables`; the adapter belongs there.
  `app/deliverables/__init__.py` becomes the side-effect import that
  registers the adapter into the registry on app startup (mirroring how
  `app/cprs/__init__.py` and `app/required_docs/__init__.py` already do
  for their handlers). Deliverables already imports from
  `app.common.requirements` for `register_requirement_type` —
  the dependency direction is correct.

### Import updates (every file that needs touching)

```
# Old → New
app.project_requirements.protocol          → app.common.requirements.protocol
app.project_requirements.registry          → app.common.requirements
app.project_requirements.aggregator        → app.common.requirements.aggregator
app.project_requirements.services          → app.common.requirements.dispatcher  (for dispatch_requirement_event)
                                            → app.requirement_triggers.services  (for hash_template_params)
app.project_requirements.schemas           → app.common.requirements.schemas     (for UnfulfilledRequirement)
                                            → app.requirement_triggers.schemas   (for WACodeRequirementTrigger* schemas)
app.project_requirements.models            → app.requirement_triggers.models     (for WACodeRequirementTrigger)
app.project_requirements.router            → app.requirement_triggers.router
app.project_requirements.adapters.deliverables → app.deliverables.requirement_adapter
```

Files needing import edits:

- `app/main.py` — top-of-file side-effect imports + `include_router` for
  the trigger router (rename `project_requirements` → `requirement_triggers`,
  variable name `requirement_triggers_router` already correct).
- `app/cprs/service.py` — `from app.common.requirements import register_requirement_type`
- `app/cprs/models.py` — `from app.common.requirements import DismissibleMixin, ManualTerminalMixin`
- `app/required_docs/service.py` — registry + `WACodeRequirementTrigger` (now from triggers module)
- `app/required_docs/models.py` — `DismissibleMixin` from common
- `app/lab_results/service.py` — `dispatch_requirement_event` from `app.common.requirements.dispatcher`
- `app/time_entries/router.py` — same dispatcher import
- `app/projects/services.py` — `dispatch_requirement_event` + `get_unfulfilled_requirements_for_project`
- `app/wa_codes/router/__init__.py` — `from app.requirement_triggers.router import router as requirement_triggers_router`
- `app/deliverables/__init__.py` — gain side-effect import of `requirement_adapter`
- `app/deliverables/requirement_adapter.py` — internal imports (registry, protocol) updated
- All test files that reference any of the old paths (the four test files
  that move; plus any tests in cprs/required_docs/deliverables that
  monkeypatch the registry by `app.project_requirements.registry`).

A pre-edit grep for `app\.project_requirements` will be the canonical
checklist; current known callers are listed in the exploration report.

### Test moves

| Test file (current path)                            | New path                                           |
| --------------------------------------------------- | -------------------------------------------------- |
| `app/project_requirements/tests/test_protocol.py`   | `app/common/requirements/tests/test_protocol.py`   |
| `app/project_requirements/tests/test_dispatch.py`   | `app/common/requirements/tests/test_dispatch.py`   |
| `app/project_requirements/tests/test_aggregator.py` | `app/common/requirements/tests/test_aggregator.py` |
| `app/project_requirements/tests/test_models.py`     | `app/requirement_triggers/tests/test_models.py`    |
| `app/project_requirements/tests/test_router.py`     | `app/requirement_triggers/tests/test_router.py`    |
| `app/project_requirements/tests/test_hash.py`       | `app/requirement_triggers/tests/test_hash.py`      |

If `test_aggregator.py` covers the `DeliverableRequirementAdapter`
specifically (as opposed to the generic aggregator walk), split that
coverage into `app/deliverables/tests/test_requirement_adapter.py`.
Tests that verify the contract belong with the contract; tests that
verify the deliverable wrapper belong with deliverables. (Decide while
moving — this is a quick read of the test bodies, not a structural
change.)

---

## Refactor 2 — `cprs` / `required_docs` router pattern

The current pattern in both modules:

```python
projects_cpr_router = APIRouter(prefix="/projects", tags=["CPRs"])
cpr_router = APIRouter(prefix="/cprs", tags=["CPRs"])
```

Both routers live in `app/cprs/router.py` (and the equivalent in
`required_docs/router.py`); both are imported into `main.py` and mounted
as siblings of `projects_router`. The collection-scoped router declares
`/projects` as its prefix from inside the child module.

### Three candidate fixes

**Option A — Single router with `/cprs` prefix; `project_id` as query
param/body field.**

- `GET /cprs?project_id=X` for list, `POST /cprs` with `project_id` in
  body, `PATCH/DELETE/POST /cprs/{cpr_id}` and `/{cpr_id}/dismiss` for
  individual ops.
- Pros: one router, no `/projects` prefix appearing in `cprs/router.py`,
  simpler `main.py` mount.
- Cons: breaks the URL hierarchy that `/projects/{id}/cprs` provides;
  list/create no longer expressed as a sub-collection of a project; the
  frontend OpenAPI client query shape changes; existing tests change.

**Option B — Keep two routers, rename for clarity, document as a
canonical pattern in `app/PATTERNS.md`.**

- Rename `projects_cpr_router` → `cpr_collection_router` and
  `cpr_router` → `cpr_item_router` (same in `required_docs`).
- Add PATTERNS.md entry: **"Project-scoped child resources expose two
  routers: a collection router under `/projects/{project_id}/<child>`
  for list/create, and an item router under `/<child>/{id}` for
  per-row mutations."**
- Pros: lowest churn, preserves URLs verbatim, documents the deliberate
  split so it stops looking ad-hoc.
- Cons: the collection router still declares `prefix="/projects"` from
  inside `cprs/required_docs` — the user's underlying objection is not
  fully addressed, just rationalized.

**Option C — Collection sub-router has no prefix; `projects_router`
mounts it under its own `/projects` prefix.** (Recommended.)

- `app/cprs/router.py` exports two routers:
  - `cpr_router` (prefix `/cprs`) — item-scoped: PATCH, DELETE, dismiss
  - `cpr_under_project_router` (no prefix; routes use
    `/{project_id}/cprs` paths) — collection-scoped: list, create
- `app/projects/router.py` does:
  ```python
  from app.cprs.router import cpr_under_project_router
  from app.required_docs.router import doc_under_project_router
  router.include_router(cpr_under_project_router)
  router.include_router(doc_under_project_router)
  ```
  `projects_router` already carries `prefix="/projects"` on its
  constructor, so the nested mount yields the same URLs as today.
- `main.py` includes only `cpr_router` (and `doc_req_router`); the
  collection routes go through `projects_router`.
- Pros: cprs/required_docs no longer declare `/projects` themselves;
  URL hierarchy is owned by the parent, child modules own only their
  own URL space; mirrors the existing nested-mount pattern in
  `app/wa_codes/router/__init__.py:15` (`router.include_router(requirement_triggers_router)`).
- Cons: introduces an import edge `app/projects/router.py →
app/cprs/router.py`. This is one-way (cprs already imports
  `Project, ProjectContractorLink` from `app.projects.models`, never
  from `projects.router`), so no circular import is created. The
  visible cost is one extra import per child module added under
  `projects` — bounded and explicit.

### Recommendation

**Option C.** It is the only option that resolves the user's objection
("cprs reaching into projects' URL namespace") without breaking URL
hierarchy. It mirrors a pattern already in use in this codebase
(`wa_codes/router/__init__.py` mounts the requirement-triggers router as
a nested mount). It scales to Sessions E (dep_filings) and F (project
requirements aggregator endpoint) cleanly: each new project-scoped
silo router exports one collection sub-router that `projects_router`
mounts. The import-direction cost (parent module pulling child router
objects at module load) is bounded and consistent with how the rest of
the codebase composes routers.

If the user prefers Option A or B, the rest of this plan adapts trivially
— this is a localized choice. Documented as an open question below.

Note: Option C composes cleanly with the lateral peer-route framework
(Refactor 3 below). Item-scoped peer routes (`GET /cprs/{id}/<peer>`)
attach to `cpr_router`; project-collection routes (`GET /projects/{id}/cprs`)
attach to the under-project sub-router that `projects_router` mounts.
The two router objects per module map cleanly onto the two route
shapes. This is the strongest argument for C over A or B: A flattens
project-scope into a query param (loses URL hierarchy _and_ makes peer
routes inconsistent), and B leaves the parent-prefix-from-child
awkwardness in place forever.

---

## Refactor 3 — Lateral peer-route framework (design + deferred build)

### The problem framed precisely

The user's example: field-work cluster of `lab_result`, `time_entry`,
`daily_log`, `wa_code_assignment`. These four entities expect each other
to coexist on a project. Materialization is event-driven (already
solvable with `dispatch_requirement_event` from Session B) — adding any
one creates pending placeholders for the others. Reading is the new
problem: a manager looking at a lab batch wants to see "what time entries
correspond to this batch on this project," "what daily logs cover this
batch's date and employee," "what WA codes are assigned to this project
that should bill this batch." That is 4 × 3 = 12 lateral read endpoints
just for this cluster, and there will be more clusters.

Hand-writing 12+ endpoints per cluster is the failure mode. The
discipline question is: can we declare the edges and let a factory emit
the routes?

### Design — `register_peer_query` + `create_peer_routes` factory

Two primitives, both new, both general (not requirements-specific):

**1. `app/common/peer_routes.py`** (new module, ~150 lines):

```python
# Declaration side (called from each parent module's router or service)

@register_peer_query(parent="lab_result", peer="daily_log")
async def daily_logs_for_batch(
    batch_id: int, db: AsyncSession
) -> list[ProjectDocumentRequirement]:
    """Project-scoped: returns daily-log requirements for the batch's
    project, filtered to date/employee/school of the batch."""
    batch = await db.get(SampleBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found")
    return (await db.execute(
        select(ProjectDocumentRequirement).where(
            ProjectDocumentRequirement.project_id == batch.project_id,
            ProjectDocumentRequirement.document_type == DocumentType.DAILY_LOG,
            ProjectDocumentRequirement.date == batch.date,
            ProjectDocumentRequirement.employee_id == batch.collected_by_id,
        )
    )).scalars().all()


# Factory side (called from each parent module's router/__init__.py)

cpr_router.include_router(
    create_peer_routes(parent="lab_result", parent_path_param="batch_id")
)
# Emits: GET /lab-results/{batch_id}/daily-logs    (typed list[ProjectDocumentRequirement])
#        GET /lab-results/{batch_id}/time-entries  (typed list[TimeEntry])
#        GET /lab-results/{batch_id}/wa-codes      (typed list[WorkAuthProjectCode])
# Path segment per peer derived from peer name (kebab-cased + pluralized).
# Response model pulled from the registered fn's return annotation.
```

The factory:

- Walks every `register_peer_query(parent=X, ...)` for the given parent
- Reads each query function's return annotation to determine the
  response model (so OpenAPI types come out correctly)
- Wires `Depends(get_db)` and the standard `PermissionChecker` for the
  reading permission
- Generates one `GET` endpoint per registered edge
- Path segment is derived from `peer` (e.g. `daily_log` →
  `/daily-logs`); overridable via `peer_path` arg on the decorator

**2. Why outside `app/common/requirements/`** — peer queries are not
tied to the `ProjectRequirement` protocol. Lab batches, time entries,
and `WorkAuthProjectCode` rows are operational data that don't implement
the protocol (PLANNING.md §2.2 explicitly excluded `SampleBatch` from
requirements). The peer-route framework must work for any project-scoped
resource. So `app/common/peer_routes.py` sits alongside, not inside,
`app/common/requirements/`. Requirement-implementing entities can be
peers, but the framework doesn't require it.

### Where each peer query lives

Per the user's directive ("the router should live under the relevant
domain, and permit for these cases the importing of models and services
from other modules"):

- A peer query for `parent=lab_result, peer=daily_log` lives in
  `app/lab_results/peer_queries.py` (or the router file).
- It imports `ProjectDocumentRequirement` from `app.required_docs.models`
  — this is a legal direction (`lab_results` consumes `required_docs`'s
  public model surface).
- The reverse query (`parent=daily_log, peer=lab_result`) lives in
  `app/required_docs/peer_queries.py` and imports `SampleBatch` from
  `app.lab_results.models`.
- These reciprocal imports are not circular because they are
  read-direction-only at the model level — no module imports another's
  router or service.
- Each parent module's router file does
  `router.include_router(create_peer_routes(parent="lab_result", ...))`
  to install the generated peer endpoints onto its own item router.

### Project scoping is enforced by the query, not the framework

Each query function is responsible for:

1. Looking up the parent entity to extract its `project_id`.
2. Filtering peer rows by that `project_id`.
3. Returning the project-scoped form (e.g. `WorkAuthProjectCode`, not
   `WACode`).
4. Returning 404 if the parent does not exist.

The framework does not impose project scoping — it would have to know
each entity's `project_id` lookup, which varies per type. Keeping
project-scoping inside each query function is the cheapest, most
honest design.

### Closure rollup — out of scope of this primitive

Set-level closure aggregation ("are all members of the field-work
cluster fulfilled for this project?") stays in `app/common/requirements/`
and is built **only when a closure consumer needs it** (likely never —
the existing per-requirement aggregator already gives one
unfulfilled-list per project, which is what closure gates need). The
peer-route framework is read-side navigation only.

### Materialization side stays as-is

Adding a `lab_result` triggers `LAB_RESULT_CREATED` (new event in
`app/common/enums.py:RequirementEvent` when needed). Handlers in
`time_entries`, `required_docs`, etc., subscribe to that event via the
existing `register_requirement_type(events=[...])` decorator and create
their pending peers. No new primitive is needed for the write side; the
existing dispatch already covers it.

### Sequencing — when does the framework primitive ship?

Three options for _this_ refactor session:

**Option I — Build the primitive now, no concrete edges.** Add
`app/common/peer_routes.py`, write the factory and decorator, write the
factory's tests. Sessions E and F register edges as they need them.
_Risk:_ premature — primitive without consumer; CLAUDE.md guidance
discourages this.

**Option II — Defer entirely. Build when first edge is needed.** This
refactor only does Refactors 1 and 2. The first peer endpoint that gets
wired (likely in Session E or a follow-up) brings the primitive with it.
_Risk:_ the first wirer has to do double duty — primitive design plus
their own session work.

**Option III — Defer the build, lock the design here.** This refactor
does 1 and 2 and **records the design in ROADMAP.md as a planned phase
(Phase 6.7 — Lateral Peer-Route Framework)** with the API sketched
above. The first session that lands a lateral peer endpoint executes
Phase 6.7 first as its prerequisite.

**Recommendation: Option III.** It honours the "no infrastructure
without a consumer" principle while preventing redesign churn — the
sketch above, if accepted, is the contract that the eventual builder
implements verbatim. Adding it to ROADMAP.md gives the design a stable
home and unblocks Session E/F planning.

### Admin-introspection layer (added to Phase 6.7 scope)

The factory alone gives typed individual edges, but admins still need
to _review_ which clusters exist and _inspect_ what's attached to a
specific entity. Without an introspection layer, admins must read
source code or READMEs to discover lateral relationships. Three
read-only endpoints solve this:

```python
# app/common/peer_routes.py — additions
def register_requirement_set(
    name: str,
    members: list[str],          # entity_type strings
    description: str | None = None,
) -> None: ...

# app/requirement_sets/router.py — new admin module
GET /requirement-sets
  -> list all registered sets (admin overview)
GET /requirement-sets/{entity_type}
  -> sets that include this entity_type (filtered to where it's a parent)
GET /requirement-sets/{entity_type}/{entity_id}
  -> full instantiated cluster state for this entity (typed payload
     keyed by peer entity_type; response model dynamically constructed
     per set via pydantic.create_model — same pattern as
     create_guarded_delete_router's {Model}Connections)
```

Sets remain developer-defined (no CRUD on `/requirement-sets`, no
`requirement_sets` table) per Decision #7. The introspection makes
sets visible to admins; changing them remains a developer task.

Closure state (`is_fulfilled` / `is_dismissed`) surfaces in the by-id
payload where peers implement the `ProjectRequirement` protocol;
non-requirement peers (operational data) appear without closure state.

The by-id endpoint is the heaviest (N queries per request, one per
peer type per set the entity belongs to). It's intended for admin
review and manager-UX "show me everything attached" views, not
high-frequency polling. Routine reads continue to hit individual
`GET /<parent>/{id}/<peer>` endpoints.

`app/requirement_sets/` is a small module: router + schemas + tests.
No DB tables, no service layer beyond the registry walk.

### What ROADMAP.md gains

A new section after Phase 6.5 covering the framework primitives and
the introspection layer (now landed). Both ship together in the first
Phase 6.7 session — the first concrete consumer registers a set
alongside its peer queries so the introspection endpoints have
something to expose from day one.

---

## Path canonicalization for upcoming sessions

These paths must be locked **now**, before Session E starts, so the
implementation sessions don't redebate them.

### Session E — Silo 3: DEP filings

Single module `app/dep_filings/` (consistent with `lab_results/`, which
holds both admin config tables and operational entity tables in one
module):

```
app/dep_filings/
├── __init__.py                       (side-effect import of service for handler registration)
├── README.md
├── models.py                         (DEPFilingForm + ProjectDEPFiling)
├── schemas.py
├── service.py                        (ProjectDEPFilingHandler + materializer)
├── router.py                         (exports two routers per Option C below)
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_router.py
    ├── test_dispatch.py
    └── test_aggregator.py
```

Routers (assuming Option C is accepted):

- `dep_filing_router` — prefix `/dep-filings`, item-scoped + admin form
  CRUD endpoints (`/dep-filings/forms` for the admin-managed
  `dep_filing_forms` table; `/dep-filings/{id}` and
  `/dep-filings/{id}/dismiss` for instances)
- `dep_filing_under_project_router` — no prefix; routes use
  `/{project_id}/dep-filings` (list, manager-UX bulk POST `{form_ids: [...]}`)
- `app/projects/router.py` mounts the under-project router
- `main.py` includes only `dep_filing_router`

**User confirmed: single `app/dep_filings/` module**, matching the
`lab_results/` precedent. The module owns both the admin form config
and the per-project filing instances; route prefixes split them
(`/dep-filings/forms` for admin config CRUD; `/dep-filings/{id}` for
instances; `/projects/{id}/dep-filings` mounted via the under-project
sub-router for the manager UX bulk-POST).

### Session F — Closure-gate integration + project-status surface

- `lock_project_records()` extension and `derive_project_status()`
  changes stay in `app/projects/services.py` (no new module).
- New endpoint `GET /projects/{project_id}/requirements` lives in
  `app/projects/router.py` directly — it is a project-level read that
  walks the registry via `get_unfulfilled_requirements_for_project()`;
  it does not belong in any silo module. Returns
  `list[UnfulfilledRequirement]` from `app.common.requirements.schemas`.
- No new module or top-level router is added in Session F.

---

## Memory updates

These updates land during this refactor session, not during Sessions E
or F.

### New feedback memory — `feedback_module_organization.md`

> **Domain-based module organization with strict hierarchy.**
>
> Shared/contract primitives belong under `app/common/<topic>/` (e.g.
> `app/common/requirements/` for protocol/registry/aggregator/dispatcher).
> Domain-specific config and routes belong in their own named module
> whose **name matches what the module owns** (e.g.
> `app/requirement_triggers/` owns the `WACodeRequirementTrigger` model
> and `/requirement-triggers` route — not `app/project_requirements/`,
> which is broader than the contents).
>
> Cross-module imports must reflect a strict hierarchy: the contract
> layer imports nothing from concrete implementations; implementations
> import only from the contract layer plus their own dependencies.
> Read-only adapters (e.g. `DeliverableRequirementAdapter`) live with
> the domain they wrap, not in the contract layer.
>
> URL hierarchy is owned by the parent: child modules export sub-routers
> with no parent prefix; parent modules mount them. Child modules never
> declare the parent's URL prefix from inside their own router file.
>
> When a new requirement-style abstraction lands, factor the same way
> from day one: contract → implementations, never co-located.
>
> **Why:** Conflating contract with one specific config (the
> `project_requirements/` mix during Phase 6.5 Sessions A–D) makes
> downstream modules import primitives from a path that suggests
> "everything related lives here," obscuring the hierarchy and making
> later splits expensive (every silo imported from the wrong path).
> Letting children declare the parent's URL prefix puts URL-namespace
> ownership in the wrong place and accumulates as more children are
> added.
>
> **How to apply:** Before adding a new module, ask whether its contents
> are (a) a contract that other modules will implement (→ `app/common/`),
> (b) a specific data model + its routes (→ named after what it owns),
> or (c) a wrapper around an existing domain (→ inside that domain's
> module). If the answer is mixed, split before writing the second
> file. For routers, ask whether the URL hierarchy you are about to
> declare belongs to this module or to a parent — if parent, export a
> no-prefix sub-router and let the parent mount it.

### New feedback memory — `feedback_lateral_vs_hierarchical.md`

> **Lateral peer clusters and hierarchical ownership are different
> mechanisms; do not unify them.**
>
> Some entity groups in this app are **hierarchical**: a parent owns
> children via FK, cascade governs orphaning, and the URL nests as
> `/parent/{id}/child/{id}`. Examples: `sample_type → sample_subtype`,
> `project → project_deliverable`, `work_auth → work_auth_project_code`.
> These use the existing patterns: FK + cascade, guarded-delete factory
> for top-level entities, ordinary REST URL nesting.
>
> Other entity groups are **lateral peer clusters**: peers exist
> independently, related by domain rules, no peer owns the others, and
> any peer can be the entry point for navigating to its peers. Example:
> field-work cluster — `lab_result ↔ time_entry ↔ daily_log ↔
wa_code_assignment`. These use the **peer-route framework** (Phase
> 6.7, deferred): declarative `@register_peer_query(parent, peer)` edges
>
> - `create_peer_routes()` factory that emits typed
>   `GET /<parent>/{id}/<peer>` endpoints from registered edges. Each
>   query function returns the **project-scoped form** of the peer
>   (`WorkAuthProjectCode`, not `WACode`), enforces project scoping
>   internally, and lives in the parent's module while importing peer
>   models from elsewhere.
>
> **Why:** Hand-writing one endpoint per pair grows N² with cluster
> size and diverges over time. The factory pattern makes lateral peers
> declarative and consistent; the existing FK/cascade patterns make
> hierarchical ownership safe and explicit. Forcing one mechanism to
> handle both loses the strengths of each.
>
> **How to apply:** Before wiring a new cross-module read endpoint,
> ask: does the parent _own_ the peer (single-direction, cascade on
> delete), or are they _allies_ (bidirectional, peer-of-peer
> navigation, materialization-on-event)? Owned → FK + nested URL.
> Allied → register a peer query and let the factory emit the route.
> Materialization (creating missing peers when one is added) stays
> event-driven through `dispatch_requirement_event` regardless.

### Updates to existing memories

- **`project_testing_progress.md`** — replace path references
  `app/project_requirements/tests/` → `app/common/requirements/tests/`
  and `app/requirement_triggers/tests/`.
- **`project_assumed_entry_closure.md`** — no change needed (does not
  reference the moved paths).
- **`feedback_router_patterns.md`** — append two bullets:
  (1) Project-scoped child-router pattern (Option C: collection
  sub-router + parent mount; child never declares the parent's prefix);
  (2) Lateral peer endpoints are factory-generated from declarative
  edges, not hand-written per pair.

`MEMORY.md` index gains two lines for the new
`feedback_module_organization.md` and
`feedback_lateral_vs_hierarchical.md` entries.

---

## Critical files to be modified

**Created:**

- `app/common/requirements/__init__.py`
- `app/common/requirements/protocol.py` (moved)
- `app/common/requirements/registry.py` (moved)
- `app/common/requirements/dispatcher.py` (renamed from services.py, scoped)
- `app/common/requirements/aggregator.py` (moved)
- `app/common/requirements/schemas.py` (UnfulfilledRequirement only)
- `app/common/requirements/README.md`
- `app/common/requirements/tests/__init__.py`
- `app/common/requirements/tests/test_protocol.py` (moved)
- `app/common/requirements/tests/test_dispatch.py` (moved)
- `app/common/requirements/tests/test_aggregator.py` (moved)
- `app/requirement_triggers/__init__.py`
- `app/requirement_triggers/models.py` (moved)
- `app/requirement_triggers/schemas.py` (WACodeRequirementTrigger\* schemas only)
- `app/requirement_triggers/services.py` (hash_template_params only)
- `app/requirement_triggers/router.py` (moved + import updates)
- `app/requirement_triggers/README.md`
- `app/requirement_triggers/tests/__init__.py`
- `app/requirement_triggers/tests/test_models.py` (moved)
- `app/requirement_triggers/tests/test_router.py` (moved)
- `app/requirement_triggers/tests/test_hash.py` (moved)
- `app/deliverables/requirement_adapter.py` (moved from project_requirements/adapters)

**Deleted:**

- `app/project_requirements/` (entire directory) once moves are complete

**Modified (import updates):**

- `app/main.py` — side-effect imports, router includes (also Option C
  router mounting if accepted)
- `app/cprs/service.py`, `app/cprs/models.py`, `app/cprs/router.py`
  (Option C only — split into two routers)
- `app/required_docs/service.py`, `app/required_docs/models.py`,
  `app/required_docs/router.py` (Option C only — split into two routers)
- `app/deliverables/__init__.py` — add side-effect import
- `app/lab_results/service.py`
- `app/time_entries/router.py`
- `app/projects/services.py`
- `app/projects/router.py` (Option C only — mount sub-routers)
- `app/wa_codes/router/__init__.py`

---

## Verification

1. `git mv` the files where possible to preserve history; otherwise
   create + delete.
2. Run a global grep for `app.project_requirements` and
   `app\.project_requirements\.` — must return zero results after
   updates.
3. Run a global grep for `projects_cpr_router`, `projects_doc_router`
   (should be replaced under Option C), `cpr_router`, `doc_req_router`
   (should still exist as item routers).
4. `.venv/Scripts/python.exe -m pytest app/ -v` — full suite (693 tests
   currently). All must remain green; no test logic changes, only
   import path updates.
5. Spot-check that the OpenAPI schema at `/openapi.json` produces the
   identical URL set as before the refactor (frontend OpenAPI client
   regen should be a no-op for URL paths). Tag names may shift
   (`Requirement Triggers` stays — the router string was unchanged).
6. Confirm side-effect registration still fires by reading
   `/openapi.json` for routes contributed by `cprs`, `required_docs`,
   `deliverables` adapter (the deliverable adapter has no routes, but
   its handler must still appear in registry walks — covered by the
   moved `test_aggregator.py`).
7. Manual smoke: `just api`, hit `GET /requirement-triggers` and
   `GET /projects/1/cprs` to confirm the route mounting works
   end-to-end.

---

## Resolved decisions

1. **Router pattern: Option C** (confirmed). Each project-scoped child
   module exports two routers: an item router with prefix `/<resource>`
   and a no-prefix under-project sub-router. `projects_router` mounts
   the under-project sub-routers. `main.py` includes only the item
   routers (and `projects_router`). Peer endpoints, when added later
   under Phase 6.7, attach to the item router via
   `cpr_router.include_router(create_peer_routes("cpr", "cpr_id"))`.

2. **Peer-route framework sequencing: Option III** (confirmed). This
   refactor records the design in ROADMAP.md as Phase 6.7 with the
   API sketched in Refactor 3 above. The framework primitive
   (`app/common/peer_routes.py`) ships as Phase 6.7, executed as the
   prerequisite step of the first session that wires a concrete peer
   endpoint. No factory code, no decorator code, no consumer wiring
   in this session.

3. **DEP filings module shape: single `app/dep_filings/` module**
   (confirmed earlier).

## Out of scope (flagged for later)

- **`required_docs` module name** — the model is
  `ProjectDocumentRequirement`, the route is `/document-requirements`,
  the module is `required_docs`. By the new naming principle,
  `app/document_requirements/` would match the model and route. Out of
  scope of the current refactor; recommend a small stand-alone rename
  session once Session E/F land, since touching it now means rebasing
  Session D's CPR work on a moving target.

---

## Sequencing

This refactor is one focused session ("Session E0" — pre-Session E
infrastructure cleanup). It must complete and tests must be green before
Session E (DEP filings) starts so Session E lands on the new paths and
the new router pattern from day one.

The lateral peer-route framework (Refactor 3) does **not** ship in this
session under the recommended Option III — only its design lands in
ROADMAP.md. The framework's primitives ship as Phase 6.7 when the first
concrete peer endpoint is wired (likely during or just after Session E).
