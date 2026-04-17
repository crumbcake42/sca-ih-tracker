# SCA IH Tracker — Backend

## Build & Test

- Install: `pip install -e .`
- Run tests: `pytest tests/ -v`
- **`pytest` is not on PATH.** Use `.venv/Scripts/python.exe -m pytest` directly — do not use `source .venv/Scripts/activate`.
- **Never run `alembic` commands.** The user generates and applies all migrations manually.

---

## Documentation: What Goes Where

| File | Purpose |
|------|---------|
| `data/ROADMAP.md` | Design intent, decisions made, what's coming next |
| `data/HANDOFF.md` | Per-session continuity; non-obvious context for the current phase |
| `app/PATTERNS.md` | Cross-cutting SQLAlchemy/FastAPI patterns — read this before adding any endpoint, service, or test |
| `app/{module}/README.md` | Module purpose, non-obvious behavior, what to check before modifying |
| Inline comments | The "why" behind non-obvious logic only |

---

## Architecture Rules

### Employees vs. Users
Keep them separate. `users` = auth/permission entities. `employees` = operational/billing entities. Overlap is handled via a nullable `employee_id` FK on `users`. Do not conflate them.

### SQLAlchemy Relationships
Use string-based class references in all `relationship()` calls to prevent circular imports:
```python
relationship("School", back_populates="projects")  # correct
```
Never import the class directly in a `relationship()` argument.

### Lab Results: Config+Data Meta-Model
Do not use joined table inheritance. Sample types, subtypes, unit types, and turnaround options are admin-managed rows — adding a new type requires no migration. Validate `sample_unit_type.sample_type_id == batch.sample_type_id` in the service layer (422 on mismatch).

### AuditMixin Scope
`AuditMixin` (`created_at`, `updated_at`, `created_by_id`, `updated_by_id`) is applied to all business entity models.

**NOT applied to:** `manager_project_assignments` (already a purpose-built audit trail); `project_school_links`, `project_contractor_links`, `project_hygienist_links` (managed via parent); `users`, `roles`, `permissions` (auth layer).

**System writes** use `SYSTEM_USER_ID = 1` (defined in `app/common/config.py`). This is a seeded reserved user (`username="system"`, no valid password hash) — it makes automated writes distinguishable from human edits.

---

## Design Decisions (Permanent — Do Not Re-Add)

### `time_entries.source` — DROPPED
`created_by_id == SYSTEM_USER_ID` already encodes whether an entry was system-created. A `source` column would be redundant.

### `conflicted` Time Entry Status — DROPPED
Overlapping entries for the same employee are allowed to coexist. On overlap, the service creates `time_entry_conflict` system notes (Phase 3.6) on **both** conflicting entries (`is_blocking=True`). Neither project can close until the notes are resolved. When the overlap is cleared, the notes auto-resolve. No `conflicted` column on `time_entries`.

*Rationale: Blocking the second manager's insert with a 422 creates a race to enter first. Allowing both with blocking notes lets both projects track real work while surfacing the conflict.*

### `orphaned` Batch Status — DROPPED
Block deletion of any `time_entry` that has `active` or `discarded` batches with 409. Managers must reassign or delete those batches first. No orphan state to manage.

### Phase 5 (Observability) — Deferred Until After Phase 6
Do not implement Phase 5 before Phase 6 is complete. The app needs real production data before observability work is meaningful.

---

## Patterns Quick Reference

See `app/PATTERNS.md` for full detail. Key patterns:

1. **`db.get()` vs `select() + populate_existing=True`** — use `select()` for any GET endpoint that serializes nested relationships
2. **FK validation in early-return paths** — SQLite won't catch dangling FKs; validate at the router layer before calling services
3. **`PermissionChecker` returns the user** — `Depends(PermissionChecker("perm"))` replaces a separate `get_current_user` call
4. **`lazy="selectin"` on all serialized relationships** — required to avoid `MissingGreenlet` during response serialization
5. **Sub-router prefix on the `APIRouter` constructor**, not on `include_router()`
6. **`follow_redirects=True` on all test clients**
7. **SQLite `Numeric` columns** — cast via `Decimal(str(value))` before arithmetic
8. **Ambiguous FK** — use `foreign_keys="[Model.column]"` string form
9. **`.unique()` before `.scalars()`** when using `joinedload`
10. **Rollback test pattern** — never call `db.commit()` inside a test body
