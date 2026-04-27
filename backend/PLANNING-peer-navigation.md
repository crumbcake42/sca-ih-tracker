# Peer Dependency Navigation — Pattern Comparison

## Context

The Phase 6.7 ROADMAP entry (now superseded — see ROADMAP.md) proposed a
"peer-route factory" plus an admin-introspection layer for navigating
between operational entities that participate in the same lateral
cluster (e.g. `lab_result ↔ time_entry ↔ daily_log ↔ wa_code_assignment`).
The goal: avoid hand-writing N×N `GET /<parent>/{id}/<peer>` endpoints
as new clusters are identified.

The 2026-04-27 architecture evaluation surfaced concerns about that
direction:

- Most "peer" relationships are not symmetric — singular FK navigation
  collapses to a field on the parent's Read schema; only the
  many-to-many lateral cases need a real lookup.
- The factory generates a uniform shape for all edges, but most
  consumers want bespoke shapes (paginated + filtered for high-cardinality
  edges; embedded summary for low-cardinality FK edges).
- The introspection layer (`/requirement-sets/...`) added a third
  namespace (sets) on top of types and triggers, with dynamic Pydantic
  models per set — for a developer-defined registry that admins can
  only read, not configure.

This doc lays the two patterns side by side using concrete use cases
and pseudocode so the tradeoff is visible.

---

## Pattern A — Peer-Route Factory (current Phase 6.7 plan, now superseded)

### Shape

```python
# app/common/peer_routes.py
@register_peer_query(parent="lab_result", peer="daily_log")
async def daily_logs_for_batch(
    batch_id: int, db: AsyncSession
) -> list[ProjectDocumentRequirement]: ...

@register_peer_query(parent="lab_result", peer="time_entry")
async def time_entry_for_batch(
    batch_id: int, db: AsyncSession
) -> TimeEntry | None: ...

# In the parent module's router:
lab_results_router.include_router(
    create_peer_routes(parent="lab_result", parent_path_param="batch_id")
)
# Emits:
#   GET /lab-results/{batch_id}/daily-logs
#   GET /lab-results/{batch_id}/time-entries
#   GET /lab-results/{batch_id}/wa-codes
```

Plus the introspection layer:

```python
register_requirement_set(
    name="field_work",
    members=["lab_result", "time_entry", "daily_log", "wa_code_assignment"],
)

# Auto-emits three endpoints:
#   GET /requirement-sets
#   GET /requirement-sets/{entity_type}
#   GET /requirement-sets/{entity_type}/{entity_id}
```

The by-id endpoint walks every set the entity belongs to, fires every
peer query, and returns a dynamically constructed Pydantic model whose
fields are typed per peer.

---

## Pattern B — Two-Layer (recommended)

### Layer 1 — Embed low-cardinality peers in Read schemas

For singular FK relationships and small fixed peer sets, the related
data is loaded with `selectin` and exposed as nested fields on the
parent's Read schema. The frontend renders hyperlinks from the
embedded IDs / labels; no separate round-trip.

### Layer 2 — Hand-rolled lateral endpoints, only when consumer needs them

For genuine many-to-many lateral navigation (one parent → list of
peers), a small number of bespoke endpoints with descriptive names,
shaped to the consumer's actual need (paginated, filtered, the right
join already encoded). No factory, no decorator registry, no dynamic
response models.

---

## Use case 1 — "Show me the time entry that owns this batch"

This is a **singular FK** relationship: `SampleBatch.time_entry_id`.

### Pattern A (peer-route factory)

```python
# app/lab_results/peer_queries.py
@register_peer_query(parent="lab_result", peer="time_entry")
async def time_entry_for_batch(
    batch_id: int, db: AsyncSession
) -> TimeEntry | None:
    batch = await db.get(SampleBatch, batch_id)
    if batch is None:
        raise HTTPException(404)
    if batch.time_entry_id is None:
        return None
    return await db.get(TimeEntry, batch.time_entry_id)

# Frontend:
const { data: te } = useGetLabResultsByIdTimeEntries(batchId);
const { data: batch } = useGetLabResultsById(batchId);
// Two HTTP calls to render a "Time Entry: …" link on the batch detail page.
```

### Pattern B (embedded peer in Read schema)

```python
# app/lab_results/schemas.py
class SampleBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    time_entry_id: int | None
    time_entry: TimeEntryMini | None  # eager-loaded via selectin
    # …

# app/lab_results/models.py
class SampleBatch(Base):
    time_entry: Mapped["TimeEntry | None"] = relationship(
        "TimeEntry", lazy="selectin"
    )

# Frontend:
const { data: batch } = useGetLabResultsById(batchId);
// One call. batch.time_entry is already populated.
```

**Verdict:** Pattern B wins decisively. Singular peers don't justify a
second round-trip; `selectin` is the right tool.

---

## Use case 2 — "Show me all batches for this time entry"

This is **genuine many-to-many lateral navigation** — the time entry
doesn't carry a list of batches as a column; the FE may want filters
(status=active, date range, school) and pagination as the count grows.

### Pattern A (peer-route factory)

```python
# app/time_entries/peer_queries.py
@register_peer_query(parent="time_entry", peer="lab_result")
async def batches_for_time_entry(
    time_entry_id: int, db: AsyncSession
) -> list[SampleBatch]:
    return (await db.execute(
        select(SampleBatch).where(SampleBatch.time_entry_id == time_entry_id)
    )).scalars().all()

# Auto-emitted: GET /time-entries/{time_entry_id}/lab-results
# Returns: list[SampleBatchRead] — no pagination, no filters.

# Frontend later wants filters → factory has no story; either:
#   (a) factory grows to support optional query params (more framework)
#   (b) override and write a bespoke endpoint, abandoning the factory benefit
```

### Pattern B (bespoke endpoint with the right shape)

```python
# app/time_entries/router.py
@router.get(
    "/{time_entry_id}/batches",
    response_model=PaginatedList[SampleBatchRead],
)
async def list_batches_for_time_entry(
    time_entry_id: int,
    status: SampleBatchStatus | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    await _get_time_entry_or_404(time_entry_id, db)
    stmt = select(SampleBatch).where(SampleBatch.time_entry_id == time_entry_id)
    if status is not None:
        stmt = stmt.where(SampleBatch.status == status)
    return await get_paginated_list(stmt, db, page=page, page_size=page_size)
```

**Verdict:** Pattern B fits the FE's actual ask (filters + pagination).
Pattern A's uniform shape forces either an unfiltered firehose or a
factory expansion to retrofit query-param support.

---

## Use case 3 — "Show me daily log requirements that match this batch's (project, employee, date, school)"

True peer query: the lookup key is composite, no FK exists pointing
either direction, and the result is a small list.

### Pattern A (peer-route factory)

```python
@register_peer_query(parent="lab_result", peer="daily_log")
async def daily_logs_for_batch(
    batch_id: int, db: AsyncSession
) -> list[ProjectDocumentRequirement]:
    batch = await db.get(SampleBatch, batch_id)
    if batch is None:
        raise HTTPException(404)
    # Project scoping enforced inside the query (constraint #2 from ROADMAP)
    time_entry = await db.get(TimeEntry, batch.time_entry_id)
    if time_entry is None:
        return []
    return (await db.execute(
        select(ProjectDocumentRequirement).where(
            ProjectDocumentRequirement.project_id == time_entry.project_id,
            ProjectDocumentRequirement.employee_id == time_entry.employee_id,
            ProjectDocumentRequirement.date == time_entry.start_datetime.date(),
            ProjectDocumentRequirement.school_id == time_entry.school_id,
            ProjectDocumentRequirement.document_type == DocumentType.DAILY_LOG,
        )
    )).scalars().all()

# Auto-emitted: GET /lab-results/{batch_id}/daily-logs
```

### Pattern B (hand-rolled with a descriptive name)

```python
# app/lab_results/router.py
@router.get(
    "/{batch_id}/matching-daily-logs",
    response_model=list[ProjectDocumentRequirementRead],
)
async def list_matching_daily_logs(
    batch_id: int, db: AsyncSession = Depends(get_db),
):
    batch = await _get_batch_or_404(batch_id, db)
    if batch.time_entry is None:  # selectin-loaded
        return []
    te = batch.time_entry
    return (await db.execute(
        select(ProjectDocumentRequirement).where(
            ProjectDocumentRequirement.project_id == te.project_id,
            ProjectDocumentRequirement.employee_id == te.employee_id,
            ProjectDocumentRequirement.date == te.start_datetime.date(),
            ProjectDocumentRequirement.school_id == te.school_id,
            ProjectDocumentRequirement.document_type == DocumentType.DAILY_LOG,
        )
    )).scalars().all()
```

**Verdict:** roughly equivalent. The factory saves the
`include_router(create_peer_routes(...))` boilerplate but spends it on
decorator registration + dynamic route emission. Hand-rolled wins on
readability (the URL says exactly what it does) and on testability (no
indirection). For 3–4 such endpoints, the factory is net negative; if
the count climbed past ~8 with the same shape, the factory would start
to pay off.

---

## Use case 4 — "Admin: show me everything attached to lab_result 42"

The Phase 6.7 introspection layer's by-id endpoint.

### Pattern A (admin introspection)

```python
GET /requirement-sets/lab_result/42

# Walks every set lab_result belongs to, fires every registered peer
# query with id=42, returns a dynamically constructed Pydantic model:
{
  "entity_type": "lab_result",
  "entity_id": 42,
  "project_id": 7,
  "sets": [
    {
      "name": "field_work",
      "peers": {
        "time_entry": [...typed list of TimeEntry...],
        "daily_log": [...typed list of ProjectDocumentRequirement...],
        "wa_code_assignment": [...typed list of WorkAuthProjectCode...]
      }
    }
  ]
}
```

Implementation cost:
- `register_requirement_set(name, members)` registry
- A walker that fires N peer queries per request
- A `pydantic.create_model` call per set, typed from each peer
  query's return annotation
- An `app/requirement_sets/` module (router, schemas, tests)

Consumer cost (FE):
- A generated TypeScript type whose shape varies per `entity_type`
- A new admin UI page to render the dynamically shaped payload

### Pattern B (no special endpoint)

If an admin needs to see "everything attached," they navigate the
batch detail page. The batch's Read schema already embeds the time
entry (Use Case 1). The matching daily logs come from the bespoke
`/lab-results/{id}/matching-daily-logs` endpoint (Use Case 3). The
billable WA code is a field on the time entry's Read schema. Three
clicks, all already-built endpoints.

For developer-side debugging (which clusters exist, which handlers are
registered, which events they subscribe to), a single flat endpoint
suffices:

```python
# app/admin/router.py — read-only debug
@router.get("/admin/registry-dump")
async def registry_dump():
    return {
        "requirement_types": [
            {
                "name": name,
                "handler": handler.__name__,
                "events": [e.value for e in subscribed_events_of(handler)],
                "is_dismissable": getattr(handler, "is_dismissable", False),
                "has_manual_terminals": getattr(handler, "has_manual_terminals", False),
            }
            for name, handler in registry.handlers_by_name().items()
        ]
    }
```

One endpoint, flat data, no dynamic models. Anything an admin or
developer would actually want to know, in one place.

**Verdict:** Pattern A's introspection layer is documentation
masquerading as an API. Pattern B's `/admin/registry-dump` covers the
real use cases for ~30 LOC.

---

## Summary table

| Use case                                                  | Pattern A cost                                             | Pattern B cost                                            | Winner |
|-----------------------------------------------------------|------------------------------------------------------------|-----------------------------------------------------------|--------|
| Singular FK navigation (Use case 1)                       | Decorator + dynamic route + extra HTTP round-trip          | Read-schema field + `selectin`                            | **B**  |
| Many-to-many lateral with FE filters (Use case 2)         | Uniform shape; needs factory expansion for query params    | One bespoke endpoint, exact shape                         | **B**  |
| Composite-key peer query (Use case 3)                     | Decorator + dynamic route                                  | One descriptive endpoint                                  | **B≈A**|
| Admin "everything attached" (Use case 4)                  | New module + dynamic Pydantic models + per-set walker      | Existing endpoints + flat registry-dump endpoint          | **B**  |

---

## Where Pattern A would actually win

Be honest about when the factory pays off:

- **8+ peer edges with the same uniform shape** (no filters, no
  pagination, simple list response). Today's identified clusters do
  not meet this bar — the field-work cluster has at most 4 distinct
  many-to-many lateral edges (time-entry → batches; batch →
  matching-daily-logs; batch → triggering-wa-codes; daily-log →
  related-batches). The other "edges" in the 4×3=12 estimate are
  singular FKs that collapse to Read-schema fields.
- **Multiple developers adding clusters in parallel**, where a uniform
  pattern reduces review burden. With one developer (this project),
  the pattern is overhead.
- **Generated client side that benefits from a uniform peer-walker
  helper** in TypeScript. The current FE codegen produces one hook per
  endpoint regardless; uniformity buys nothing on the consumer side.

If those conditions appear later, the factory remains a viable
extraction. The constraints frozen in the prior ROADMAP entry
(`peer queries live in parent module`, `project scoping inside the
query`, `each peer returns the project-scoped form`) all hold equally
in Pattern B — the hand-rolled endpoints already follow them — so
extracting the factory later is a refactor, not a redesign.

---

## Recommendation

Replace the Phase 6.7 framework with this two-layer rule, written into
ROADMAP.md and `app/PATTERNS.md`:

1. **Singular peers** → embed in parent's Read schema via `selectin`
   eager-load. No new endpoint.
2. **Genuine many-to-many lateral peers** → one bespoke endpoint per
   edge, descriptive name (`/lab-results/{id}/matching-daily-logs`,
   not `/lab-results/{id}/daily-logs`), shaped to consumer need
   (filters + pagination where cardinality warrants).
3. **Developer/admin debugging** → one `GET /admin/registry-dump`
   returning flat registry contents.
4. **Factory extraction** → revisit only if 8+ edges with uniform
   shape land. The frozen design constraints carry forward; the
   primitive can be added without rewriting consumers.

The field-work cluster ships its 3–4 lateral endpoints by hand
whenever the FE asks for them, on a per-edge basis (one session per
edge per `feedback_session_segmentation.md`). No infrastructure
shipped without a consumer.
