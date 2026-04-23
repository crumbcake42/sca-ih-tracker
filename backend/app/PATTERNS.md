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

## 14. Guarded DELETE

Every deletable reference entity gets two endpoints and a shared helper:

**The helper** — `_get_{entity}_references(db, entity_id) -> dict[str, int]` — lives next to the router. It fires one `COUNT` query per referencing table and returns `{label: count}`. Use `select(func.count()).select_from(...)` rather than fetching rows — one round-trip regardless of match count.

**`GET /{entity_id}/connections`** — calls the helper and returns the dict as-is. Powers the delete-confirmation dialog in the UI.

**`DELETE /{entity_id}`** — calls the helper independently, then passes the result to `assert_deletable(refs)` from `app/common/guards.py`. If any count is nonzero, raises `HTTPException(409, {"blocked_by": [label, ...]})` listing **all** blocking reasons at once (not fail-fast). Returns 204 on success.

```python
from sqlalchemy import func, select
from app.common.guards import assert_deletable

async def _get_school_references(db: AsyncSession, school_id: int) -> dict[str, int]:
    link_count = await db.scalar(
        select(func.count()).select_from(ProjectSchoolLink)
        .where(ProjectSchoolLink.school_id == school_id)
    )
    return {"projects": link_count}

@router.get("/{school_id}/connections")
async def get_school_connections(school_id: int, db: AsyncSession = Depends(get_db)):
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return await _get_school_references(db, school_id)

@router.delete("/{school_id}", status_code=204)
async def delete_school(school_id: int, db: AsyncSession = Depends(get_db)):
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    assert_deletable(await _get_school_references(db, school_id))
    await db.delete(school)
    await db.commit()
```

**TOCTOU note:** The connections endpoint result is stale by the time DELETE fires. The DELETE handler always re-runs the reference checks regardless of what the connections endpoint returned. They share code via the helper, not via HTTP calls.

**Guard even when CASCADE is set:** If a FK has `ondelete=CASCADE`, the guard still checks it. Silently wiping related rows on delete is destructive; the guard forces an explicit unlink first.
