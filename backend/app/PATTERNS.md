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

**Testing audit fields:** Audit columns are not exposed in any Read schema, so you cannot check them from response JSON. Query the DB directly after the API call:

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

## 11. Rollback test pattern

Tests use a transaction-based rollback fixture. Each test opens a savepoint, runs, then rolls back — leaving the database clean for the next test without re-creating the schema.

**Critical:** Do not call `db.commit()` inside a test body or inside any code path exercised by a test. A commit breaks out of the savepoint and makes the transaction fixture unable to roll back, causing state to bleed between tests.

`expire_on_commit=False` is set on the test session factory. This prevents SQLAlchemy from expiring all attributes after a flush (which would require re-querying objects already loaded in the test body).

**Migrations are user-managed.** Do not run `alembic` commands. Generate and apply all migrations manually.
