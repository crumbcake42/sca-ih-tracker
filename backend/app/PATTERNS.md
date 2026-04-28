# Cross-Cutting Patterns

Patterns that apply across multiple modules. Read this before adding a new endpoint, service function, or test.

---

## 1. `db.get()` vs `select() + populate_existing=True`

**Rule:** Never use `db.get()` in a route whose return value is serialized into a response schema that includes nested relationships.

`db.get()` checks the SQLAlchemy identity map first. If the object is already cached in the session (e.g., it was just inserted or fetched earlier in the same request), it returns the cached instance without hitting the database again. The `selectin` loaders that populate child collections never re-fire, leaving those collections in an uninitialized state. FastAPI then tries to serialize them during response construction — outside an async context — and raises `MissingGreenlet`.

A secondary problem: even without `MissingGreenlet`, a cached instance may have stale child collections. If a child was added to the DB after the parent was first loaded into the identity map, `db.get()` returns the version from before the child existed.

**Fix:** Use `select()` with `populate_existing=True`:

```python
result = await db.execute(
    select(SampleType)
    .where(SampleType.id == sample_type_id)
    .execution_options(populate_existing=True)
)
st = result.scalar_one_or_none()
if not st:
    raise HTTPException(status_code=404, detail="Sample type not found")
return st
```

`populate_existing=True` forces a real database query and re-fires `selectin` loaders even when the object is already in the identity map.

**When `db.get()` is safe:** Internal lookups that are not directly serialized into a response schema — existence checks, loading a FK target to read a single field. Example:

```python
# Safe: result is not serialized; we only check a field
employee_role = await db.get(EmployeeRole, time_entry.employee_role_id)
if not employee_role:
    raise HTTPException(status_code=404, detail="Employee role not found")
if employee_role.role_type not in allowed_role_types:
    ...
```

---

## 2. FK validation in service functions with early returns

**Rule:** Any service function that validates a FK target but has a conditional early return must not be the sole place that FK is checked.

SQLite does not enforce FK constraints by default. An `INSERT` with a nonexistent FK value succeeds silently unless the application explicitly validates it.

The problem arises when a service function can return early before reaching the FK check:

```python
async def validate_employee_role_for_sample_type(time_entry_id, sample_type_id, db):
    required = await db.execute(...)  # fetch required roles
    if not required:
        return  # <-- early return: time_entry_id is NEVER checked
    
    time_entry = await db.get(TimeEntry, time_entry_id)  # never reached
    ...
```

If the sample type has no required roles, the function returns before checking whether `time_entry_id` exists. The caller then inserts a batch with a dangling FK, which SQLite allows.

**Fix:** Add an explicit existence check at the router layer before calling the service:

```python
# In the router, before any service call:
if not await db.get(TimeEntry, body.time_entry_id):
    raise HTTPException(status_code=404, detail="Time entry not found")

await validate_employee_role_for_sample_type(body.time_entry_id, body.sample_type_id, db)
```

**When to apply:** Any time a FK field is not unconditionally validated inside the service function it's passed to.

---

## 3. `PermissionChecker` returns the current user

`PermissionChecker.__call__` returns the authenticated `User` object. Use it as a dependency to both enforce permissions and capture the user in a single declaration:

```python
@router.post("/")
async def create_time_entry(
    body: TimeEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("time_entries:write")),
):
    ...
```

Do not add a separate `Depends(get_current_user)` call when `PermissionChecker` is already present. That would fire two separate dependency evaluations and decode the JWT twice.

---

## 4. AuditMixin wiring

`AuditMixin` adds `created_at`, `updated_at`, `created_by_id`, `updated_by_id` to every business entity model. These must be populated explicitly at the application layer — they are not automatic.

**On create:**
```python
obj = MyModel(**body.model_dump(), created_by_id=current_user.id)
db.add(obj)
```

**On update:**
```python
for field, value in body.model_dump(exclude_unset=True).items():
    setattr(obj, field, value)
obj.updated_by_id = current_user.id
```

**For system-initiated writes** (quick-add endpoint, status recalculation, auto-generated notes):
```python
from app.common.config import SYSTEM_USER_ID

obj = MyModel(**data, created_by_id=SYSTEM_USER_ID)
```

`SYSTEM_USER_ID = 1` is a reserved seeded user row (`username="system"`, no valid password hash). It makes automated writes distinguishable from human edits in audit queries.

**Testing audit fields:** Audit columns are not always exposed in Read schemas. When they are not, query the DB directly after the API call:

```python
obj = await db_session.get(MyModel, response.json()["id"])
assert obj.created_by_id == 1  # fake_user.id from auth_client fixture
```

Or refresh an object already in scope:

```python
await db_session.refresh(obj)
assert obj.updated_by_id == 1
```

---

## 5. `lazy="selectin"` on serialized relationships

Any relationship that appears in a Pydantic response schema must use `lazy="selectin"`. SQLAlchemy's default lazy loading raises `MissingGreenlet` when a relationship attribute is accessed outside an async context during FastAPI response serialization.

```python
class SampleType(Base, AuditMixin):
    subtypes: Mapped[list["SampleSubtype"]] = relationship(
        back_populates="sample_type",
        cascade="all, delete-orphan",
        lazy="selectin",  # required — this collection is in the response schema
    )
```

`lazy="selectin"` fires one additional `SELECT ... WHERE id IN (...)` query per relationship per request. It is not a join. For list endpoints returning many objects with nested collections, this is an N+1 risk — see the Query Performance design note in the roadmap.

---

## 6. Sub-router prefix location

Declare `prefix=` on the `APIRouter` constructor inside the sub-router file itself. Never pass `prefix=` to `include_router()`.

```python
# rfas.py — correct
router = APIRouter(prefix="/{wa_id}/rfas", tags=["RFAs"])

# work_auths/router/__init__.py — correct
router.include_router(rfas_router)  # no prefix= here
```

Putting the prefix in `include_router()` scatters route definitions across two files and makes it easy for the prefix and the route paths to fall out of sync.

---

## 7. Sub-router trailing slash and `follow_redirects`

Both `AsyncClient` fixtures in `conftest.py` use `follow_redirects=True`. FastAPI redirects requests to `/resource` → `/resource/` by default. Without this flag, test clients receive a 307 redirect instead of the actual response.

Do not work around this by changing route paths from `"/"` to `""` — FastAPI raises `FastAPIError: Prefix and path cannot be both empty` when the sub-router already has a prefix.

---

## 8. SQLite `Numeric` columns require explicit casting

SQLite returns `Numeric` (DECIMAL) columns as strings at runtime. Arithmetic on them fails silently or raises `TypeError` without an explicit cast:

```python
# Wrong — may raise TypeError or silently produce wrong results
wabc.budget = wabc.budget + rfa_bc.budget_adjustment

# Correct
from decimal import Decimal
wabc.budget = Decimal(str(wabc.budget)) + rfa_bc.budget_adjustment
```

This is a SQLite-specific quirk. PostgreSQL returns `Numeric` as `Decimal` natively and does not need this workaround. The cast is safe to leave in when migrating to PostgreSQL.

---

## 9. Ambiguous FK on `relationship()`

When two FK columns on a model both point to the same target table, SQLAlchemy cannot determine which FK a `relationship()` should use and raises `AmbiguousForeignKeysError`. Pass `foreign_keys` as a string to resolve:

```python
submitted_by: Mapped["User | None"] = relationship(
    foreign_keys="[RFA.submitted_by_id]"
)
resolved_by: Mapped["User | None"] = relationship(
    foreign_keys="[RFA.resolved_by_id]"
)
```

Use the string form (not a direct column reference) to avoid circular import issues between model files.

---

## 10. `.unique()` before `.scalars()` with `lazy="joined"` relationships

When a query loads a relationship using `lazy="joined"`, SQLAlchemy may produce duplicate rows in the result set (one per joined child row). Calling `.scalars()` directly without `.unique()` returns those duplicates.

```python
# Wrong — may return duplicate User objects if roles are joined
result = await db.execute(select(User).options(joinedload(User.roles)))
users = result.scalars().all()

# Correct
users = result.unique().scalars().all()
```

This only applies to `lazy="joined"` / `joinedload`. `lazy="selectin"` fires a separate query and does not produce duplicate rows.

---

## 12. Route registration order for overlapping POST paths

When two POST routes share the same path structure (e.g., `/{a}/{b}` and `/{id}/literal`), register the more-specific one (with a literal path segment) **first**. Starlette checks routes in registration order and does not auto-prioritise literal segments over parameters.

```python
# Correct — /{note_id}/reply registered before /{entity_type}/{entity_id}
@router.post("/{note_id}/reply", ...)        # literal "reply" → more specific
@router.post("/{entity_type}/{entity_id}", ...)  # both segments are variables
```

For a path like `/notes/42/reply`, both patterns match structurally. With `/{note_id}/reply` first, Starlette matches it correctly. The generic pattern still handles `/notes/project/42` because "42" ≠ "reply" so the more-specific pattern does not match structurally.

---

## 13. `expunge()` + nested `selectinload` for just-created objects

After committing a newly created ORM object, expunge it from the session before reloading with `selectinload`. Without expunge, the identity map returns the in-memory object whose relationship collections are in an uninitialised state. The `selectinload` secondary query is skipped ("collection already present"), leaving the attribute in a lazy state that raises `MissingGreenlet` when FastAPI serialises the response.

```python
note = Note(...)
db.add(note)
await db.commit()

# Remove from identity map so the reload gets a fresh Python object
note_id = note.id
db.expunge(note)

result = await db.execute(
    select(Note)
    .where(Note.id == note_id)
    .options(selectinload(Note.replies).selectinload(Note.replies))
)
return result.scalar_one()
```

For recursive schemas (`NoteRead.replies: list["NoteRead"]`), chain `selectinload` two levels deep. One level is not enough — the replies' `replies` collections also need to be DB-loaded before serialisation.

`db.expire_all()` is NOT a safe substitute — it disrupts async session cursor creation. `db.expunge(specific_obj)` is targeted and harmless.

---

## 11. Rollback test pattern

Tests use a transaction-based rollback fixture. Each test opens a savepoint, runs, then rolls back — leaving the database clean for the next test without re-creating the schema.

**Critical:** Do not call `db.commit()` inside a test body or inside any code path exercised by a test. A commit breaks out of the savepoint and makes the transaction fixture unable to roll back, causing state to bleed between tests.

`expire_on_commit=False` is set on the test session factory. This prevents SQLAlchemy from expiring all attributes after a flush (which would require re-querying objects already loaded in the test body).

**Migrations are user-managed.** Do not run `alembic` commands. Generate and apply all migrations manually.

---

## 15. Factory query-param column filters

Every `create_readonly_router`-backed `GET /` endpoint accepts column-filter query params automatically — no per-entity boilerplate required.

**Filter shapes:**

- `?col=v` — exact match (`col = v`)
- `?col=v1&col=v2` — OR within one column (`col IN (v1, v2)`)
- `?col_a=v1&col_b=v2` — AND across columns (both clauses apply)
- `?col=v&search=q` — column filter AND search compose (AND)

**Filterable set:** all scalar columns except `AuditMixin` fields (`created_at`, `updated_at`, `created_by_id`, `updated_by_id`). Relationship attributes are excluded. The set is computed once at factory-construction time via `app/common/introspection.filterable_columns()`.

**Reserved params** (`skip`, `limit`, `search`) are never treated as column names.

**Error responses (422):**

```
# Unknown column names — all listed, sorted alphabetically
{"detail": "Unknown query parameters: bad_col, other_col"}

# Type coercion failure — first bad value reported
{"detail": "Invalid value for 'id': 'not-a-number'"}
```

**Consumed via `Request`** — column filters do not appear in the OpenAPI schema. This is intentional: the filterable surface is dynamic and adding it to OpenAPI would require per-entity schema overrides that defeat the purpose of the factory.

**When adding a new factory-backed entity**, column filtering works automatically. No changes needed in the factory or the entity module unless a column should be excluded — in which case add it to `AuditMixin` (permanent audit fields) or file a separate request to widen `filterable_columns()`.

---

## 16. Model properties and Pydantic `from_attributes=True`

Pydantic's `from_attributes=True` reads `getattr(orm_obj, field_name)`. Plain type annotations work for ORM **columns** and **`@property`** methods. They fail for plain Python **methods**: `obj.is_fulfilled` returns the bound method object, which Pydantic coerces to `True` (truthy) silently.

**Rule: ORM model methods that need serialization must be `@property`.** Then plain annotation works in the schema:

```python
# model
@property
def is_fulfilled(self) -> bool:
    return self.rfp_saved_at is not None

# schema
class MyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    is_fulfilled: bool  # works because model has @property
```

Non-ORM adapters (e.g. `DeliverableRequirementAdapter`) keep `is_fulfilled` as a plain method since they are never serialized via `from_attributes=True` — the aggregator calls `req.is_fulfilled()` directly.

**Python 3.14 `date` field shadowing:** If a schema field is named `date` with annotation `date | None`, Python 3.14's annotation evaluation sees `date` as the default value `None` in the class namespace, not the `datetime.date` type. Fix with an import alias:

```python
from datetime import date as DateField

class MySchema(BaseModel):
    date: DateField | None = None  # not `date: date | None`
```

---

## 17. Project-scoped child router

**URL namespace owns the code.** Any route whose path starts with `/<domain>/` must live in `app/<domain>/router/`. `app/projects/router/__init__.py` must not import from outside `app/projects/`.

When a child module exposes both **item-scoped ops** (`PATCH/DELETE/dismiss` on `/{resource}/{id}`) and **project-scoped ops** (`GET/POST` on `/projects/{project_id}/{resource}`):

- **Item ops** stay in `app/{resource}/router.py` with `prefix="/{resource}"` — mounted directly in `main.py`.
- **Project-scoped ops** live in `app/projects/router/{resource}.py` with `prefix="/{project_id}/{resource}"` on the constructor — mounted inside `app/projects/router/__init__.py` alongside the other projects sub-routers.

```python
# app/cprs/router.py — item ops only
router = APIRouter(prefix="/cprs", tags=["CPRs"])

@router.patch("/{cpr_id}", ...)
@router.delete("/{cpr_id}", ...)

# app/projects/router/cprs.py — project-scoped ops
from app.cprs.models import ContractorPaymentRecord   # OK: read-only model import

router = APIRouter(prefix="/{project_id}/cprs", tags=["CPRs"])

@router.get("/", ...)
@router.post("/", ...)

# app/projects/router/__init__.py — only wires its own sub-routers
from .cprs import router as CprsRouter

router = APIRouter(prefix="/projects", ...)
router.include_router(CprsRouter)                     # resolves to /projects/{project_id}/cprs

# app/main.py
from app.cprs.router import router as cprs_router

app.include_router(cprs_router)                       # resolves to /cprs/{cpr_id}
app.include_router(projects_router)                   # resolves to /projects/...
```

**Tradeoff to be aware of:** reading all CPR API behaviour requires looking in two places — `app/cprs/router.py` for item ops and `app/projects/router/cprs.py` for project ops. Note this split in the child module's README.

See also: PATTERNS.md #6 (prefix on the constructor, not in `include_router()`).

---

## 14. Guarded DELETE

Use `create_guarded_delete_router` from `app/common/factories.py` for any reference entity that needs a guarded DELETE plus a typed `/connections` view. The factory generates a named `{ModelName}Connections` Pydantic schema (typed in OpenAPI) and emits `GET /{id}/connections` + `DELETE /{id}`.

```python
from app.common.factories import create_guarded_delete_router
from app.contractors.models import Contractor
from app.projects.models.links import ProjectContractorLink

router.include_router(
    create_guarded_delete_router(
        model=Contractor,
        not_found_detail="Contractor not found",
        path_param_name="contractor_id",
        refs=[
            (ProjectContractorLink, ProjectContractorLink.contractor_id, "project_contractors_links"),
        ],
    )
)
```

`refs` is a list of `(selectable, fk_column, label)` tuples — one per referencing table. `selectable` is the ORM model class or `Table` used as the `select_from` target. `label` is the public response key; **preserve it verbatim** when migrating from hand-rolled handlers — it is part of the API contract.

**`GET /{id}/connections`** — returns `{label: count}` for every ref. Response is typed as `{ModelName}Connections` in OpenAPI (no more `unknown` in the generated client).

**`DELETE /{id}`** — re-runs all reference counts independently, then calls `assert_deletable` from `app/common/guards.py`. Returns 409 `{"blocked_by": [...labels...]}` if any count is nonzero — all blockers listed at once, not fail-fast. Returns 204 on success.

**TOCTOU note:** The connections endpoint result is stale by the time DELETE fires. The DELETE handler always re-runs the reference checks regardless of what the connections endpoint returned.

**Guard even when CASCADE is set:** If a FK has `ondelete=CASCADE`, the guard still checks it. Silently wiping related rows on delete is destructive; the guard forces an explicit unlink first.

---

## 18. Documenting structured non-default error responses in OpenAPI

FastAPI only includes the `response_model` schema in the OpenAPI spec by default. Any 409 (or other non-422/200) response whose `detail` is a structured dict (not a plain string) is invisible to the generated client unless explicitly declared.

Use the `responses=` argument on the route decorator to register a Pydantic model for each structured error shape:

```python
@router.post(
    "/{project_id}/close",
    status_code=200,
    response_model=ProjectStatusRead,
    responses={
        409: {
            "model": CloseProjectConflictDetail,
            "description": "Blocking notes or unfulfilled requirements exist.",
        }
    },
)
```

**When to use:** Any time a route raises `HTTPException(status_code=4xx, detail=<dict>)` whose shape the FE needs to branch on. Plain-string details (e.g. `"Project not found"`) do not need this — only structured dicts.

**Schema design:** Prefer a single schema with optional keys over a `Union` discriminated union. The codebase has no `discriminator=` precedent and key-disjoint shapes are easier for FE callers to narrow on key presence. Both keys should be `list[T] | None = None`.

**`responses={}` is documentation only** — it does not change runtime behavior. The `HTTPException` detail is serialized as-is; FastAPI does not validate it against the declared `model`. Keep the schema in sync with the actual `detail` structure manually.
