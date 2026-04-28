---
name: Router and async SQLAlchemy patterns
description: Patterns confirmed by the user for sub-router structure, async relationships, and SQLite quirks
type: feedback
originSessionId: 585d7895-3d9e-468e-a08e-6a0bbf9fea0f
---
## Sub-router prefix location

Declare the prefix inside the sub-router file itself, not in the `include_router()` call.

```python
# rfas.py
router = APIRouter(prefix="/{wa_id}/rfas", tags=["RFAs"])

# __init__.py
router.include_router(RFAsRouter)  # no prefix= here
```

**Why:** User explicitly rejected the alternative. Keep it consistent with this pattern across all sub-routers.

**How to apply:** Always set `prefix=` on the `APIRouter(...)` constructor in the sub-router file. Never pass `prefix=` to `include_router()`.

**Exception — project-scoped child resources** (cprs, required_docs, dep_filings, etc.): the child module exports a *no-prefix* under-project sub-router whose routes use `/{project_id}/<resource>` paths, and `app/projects/router.py` mounts it. Item-scoped operations (PATCH/DELETE/dismiss + future peer routes) live on a separate `<resource>_router` with `prefix="/<resource>"`. The child module never declares `prefix="/projects"` itself — URL hierarchy is owned by the parent.

```python
# app/cprs/router.py
cpr_router = APIRouter(prefix="/cprs", tags=["CPRs"])  # item-scoped
cpr_under_project_router = APIRouter(tags=["CPRs"])    # collection-scoped, no prefix

@cpr_under_project_router.get("/{project_id}/cprs")  # mounted under /projects
@cpr_router.patch("/{cpr_id}")                       # mounted directly

# app/projects/router.py
from app.cprs.router import cpr_under_project_router
router.include_router(cpr_under_project_router)  # router carries prefix="/projects"

# app/main.py
app.include_router(projects_router)
app.include_router(cpr_router)
```

Mirrors the wa_codes nested-mount pattern (`app/wa_codes/router/__init__.py` mounting `requirement_triggers_router`).

---

## Lateral peer endpoints — factory-generated, not hand-written

For lateral peer clusters (e.g. lab_result ↔ time_entry ↔ daily_log ↔ wa_code_assignment), do NOT hand-write `GET /<parent>/{id}/<peer>` endpoints per pair. Use the peer-route framework (`app/common/peer_routes.py` — Phase 6.7, ships with first consumer):

- `@register_peer_query(parent="lab_result", peer="daily_log")` decorates a query function that returns the project-scoped form of the peer
- `create_peer_routes(parent="lab_result", parent_path_param="batch_id")` factory emits typed GET routes from all registered edges
- The query function lives in the parent's module, imports peer models from elsewhere, looks up the parent's `project_id`, and filters peers to that project

See `feedback_lateral_vs_hierarchical.md` for when to use this vs FK + nested URL.

---

## FastAPI trailing-slash redirect handling

Use `follow_redirects=True` on both AsyncClient fixtures in `conftest.py`. Do not change route paths from `"/"` to `""` to work around this — FastAPI raises `FastAPIError: Prefix and path cannot be both empty` when the sub-router has no prefix.

**Why:** Routes are defined at `"/"` (FastAPI canonical form). httpx doesn't follow redirects by default. `follow_redirects=True` is the cleanest fix without restructuring routes.

---

## SQLAlchemy async: lazy loading on serialized relationships

Use `lazy="selectin"` on any relationship that will be included in a FastAPI response schema. SQLAlchemy's default lazy loading raises `MissingGreenlet` when accessed outside an async context during response serialization.

```python
project_codes: Mapped[list["RFAProjectCode"]] = relationship(
    back_populates="rfa", cascade="all, delete-orphan", lazy="selectin"
)
```

**How to apply:** Any time a model's relationship is included in a Pydantic `response_model`, add `lazy="selectin"` to that relationship.

---

## SQLite Numeric arithmetic

SQLite returns `Numeric` columns as strings at runtime. Arithmetic requires an explicit cast:

```python
wabc.budget = Decimal(str(wabc.budget)) + rfa_bc.budget_adjustment
```

**How to apply:** Always wrap SQLAlchemy `Numeric` column reads in `Decimal(str(...))` before doing arithmetic in SQLite-backed code.

---

## Ambiguous FK on relationships

When multiple FK paths exist between two tables, SQLAlchemy raises an error on `relationship()`. Pass `foreign_keys` as a string to resolve:

```python
submitted_by: Mapped["User | None"] = relationship(foreign_keys="[RFA.submitted_by_id]")
```

---

## `db.get()` vs `select()` for responses that include selectin relationships

Never use `db.get()` in a route whose return value is serialized with nested relationships. `db.get()` returns the identity-map cached instance and may not fire `selectin` loaders, causing `MissingGreenlet` during serialization.

Use `select()` with `populate_existing=True` instead:

```python
result = await db.execute(
    select(SampleType)
    .where(SampleType.id == sample_type_id)
    .execution_options(populate_existing=True)
)
st = result.scalar_one_or_none()
```

`populate_existing=True` forces a re-query even when the object is already in the identity map, ensuring child collections added after the initial load are reflected. Required for correctness in tests that add children then GET the parent in the same session.

**Why:** `db.get()` hits the identity map first; if the object is cached with stale/empty collections, the selectin loader never re-fires. `select()` without `populate_existing` can still return the stale cached instance. Only `select() + populate_existing=True` guarantees a fresh fetch with all selectin loads.

**How to apply:** Any `get_X_or_404()` helper whose result is returned directly by a GET endpoint (i.e., serialized into a `response_model` that includes nested objects) should use this pattern.
