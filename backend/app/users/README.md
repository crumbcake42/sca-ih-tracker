## Purpose

Owns authentication and permission entities: `User`, `Role`, and `Permission`. A user is an auth/access control entity — a person (or system process) that can call the API and has a defined set of permissions.

This module does **not** own employee operational data (billing rates, role certifications, field assignments). The connection between a user and an employee is a nullable `employee_id` FK on `User` — ownership of that relationship belongs to the calling context, not this module.

---

## Non-obvious behavior

**`PermissionChecker` returns the current user.** The `PermissionChecker(permission_name)` dependency in `dependencies.py` both enforces that the authenticated user has the required permission *and* returns the `User` object. Use it as the sole auth dependency on any protected endpoint — do not add a separate `get_current_user` call alongside it, as that issues a redundant DB query.

```python
# Correct — one dependency does both jobs
async def my_endpoint(current_user: User = Depends(PermissionChecker("project:edit"))):
    ...

# Wrong — redundant query
async def my_endpoint(
    _: None = Depends(PermissionChecker("project:edit")),
    current_user: User = Depends(get_current_user),
):
    ...
```

**`id=1` is the reserved system user.** The row with `username="system"` and `id=1` is seeded by `app/scripts/db.py` and referenced as `SYSTEM_USER_ID` in `app/common/config.py`. It has no valid password hash and cannot log in. It is used as `created_by_id` / `updated_by_id` on any write performed by an automated service function rather than a human request. Never delete this row or reassign its ID.

**RBAC is role → permissions M2M.** A `User` has one `Role`; a `Role` has many `Permission` rows via the `role_permissions` association table. `PermissionName` in `common/enums.py` is the source of truth for all permission strings — never pass raw strings to `PermissionChecker`.

**`UserRole` and `RoleName` are separate enums that happen to share the same values.** `RoleName` is used for seeding/identifying role rows in the DB. `UserRole` is used for display and access-check logic. They must stay in sync.

---

## Before you modify

- **`PermissionChecker`** is imported in nearly every router in the project. If you change its return type or call signature, audit every router that depends on it.
- **Adding a new permission** requires: (1) adding it to `PermissionName` in `common/enums.py`, (2) assigning it to the appropriate role in `app/scripts/db.py`, (3) re-running the db init script in dev.
- **Never delete `id=1`** — doing so will break any audited write that uses `SYSTEM_USER_ID`.
