---
name: Testing infrastructure and progress
description: What was built, what's working, and what still needs to be written for the test suite
type: project
---

We set up a full testing foundation using approach C (layered: breadth via integration tests + depth via targeted unit/service tests). Here is the exact state of play.

## What was built

**Infrastructure:**
- `conftest.py` (root level) — shared fixtures: `test_engine` (module-scoped, in-memory SQLite), `db_session` (per-test rollback transaction), `client` (unauthenticated), `auth_client` (overrides `get_current_user` with a fake superadmin, overrides `get_db`)
- `tests/conftest.py` — gutted, just a comment pointing to root conftest
- `pyproject.toml` — added `pytest-cov` to dev deps, `test` and `test-cov` scripts, `[tool.coverage.run]` and `[tool.coverage.report]` sections, `testpaths = ["tests", "app"]` for colocated test discovery

**Colocated unit tests (no DB, no fixtures):**
- `app/common/test_formatters.py` — tests `format_phone_number` in isolation
- `app/common/test_schemas.py` — tests `OptionalField` / `empty_to_none`
- `app/employees/test_schemas.py` — tests `EmployeeBase` field validation (phone, adp_id, email) and the `end_after_start` model_validator on `EmployeeRoleCreate`; all calls to `EmployeeBase(...)` have `# type: ignore` due to a known Pylance false positive (see below)

**Integration tests (real in-memory DB, fake auth):**
- `app/schools/test_router.py` — covers the factory-generated list endpoint (pagination, search, auth enforcement, invalid params), the hand-written detail endpoint (lookup by ID and code, 404s), and batch import (happy path, bad row, mixed valid/invalid, duplicate, wrong file type)
- `app/employees/test_roles.py` — covers basic CRUD and all overlap detection branches (completely inside, trailing edge, exact boundary on end_date, open-ended existing role, non-overlapping before/after, different role types don't conflict), plus PATCH end_date validation

## What is NOT yet written

These are the remaining areas worth covering, roughly in priority order:

1. **`app/projects/` router** — full CRUD with permission checks (`project:create`, `project:edit`, `project:delete`). The `PermissionChecker` dependency needs testing: confirm a user without the right permission gets 403, not just that a superadmin can do everything.
2. **`app/projects/services.py` — `process_project_import()`** — the contractor link history logic (`is_current` flag, reassignment, multiple historical links). This is the most complex business logic in the codebase and should be tested at the service layer directly (pass a db session, not via HTTP) as well as through the import endpoint.
3. **`app/users/router/auth.py`** — the `POST /auth/token` endpoint: valid credentials → 200 + JWT, wrong password → 401, unknown username → 401, expired token on a protected route → 401.
4. **Factory router parametrization** — the same factory backs contractors, hygienists, wa_codes, and deliverables. `app/schools/test_router.py` covers the factory behavior, but if you want explicit regression coverage for each module, add a thin parametrized test in `tests/` that hits each module's list endpoint with a seeded record.
5. **`app/common/crud.py` — `get_by_ids()`** — the 404-on-missing-ids path. Currently untested.

## Known issues / decisions made

- **Pylance false positive on `EmployeeBase(...)`**: `OptionalString = OptionalField[str]` goes through a generic TypeAlias that Pylance can't resolve to `str | None`, so it flags optional fields as missing required args. Suppressed with `# type: ignore` in the test file. The user decided not to refactor the production schema code for now but may revisit.
- **`AuditMixin` fields**: `School` (and other models using `AuditMixin`) have `created_by_id` / `updated_by_id` FK columns pointing to `users`. In tests, we never seed a real user, so those stay `NULL`. This works because the columns are `nullable=True`. If that changes, the school/employee fixtures will need a seeded user.
- **`test_engine` is module-scoped**: Schema is created once per test file. Each test rolls back via the transaction fixture. If you see tests bleeding state into each other, check whether a `db.commit()` is being called inside the test (it would break out of the rollback).
- **Why `auth_client` overrides `get_current_user` instead of issuing a JWT**: avoids needing a populated users/roles/permissions table. The fake user has all permissions. For permission-specific tests (403 cases), you'll need a second fixture with a restricted role — or parametrize the fake user's permissions.

## How to run

```bash
pytest                          # all tests
pytest app/employees/           # just employee tests
pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```
