## Purpose

Owns `Employee` records and time-bound `EmployeeRole` instances. An employee is an operational/billing entity — a person who performs field work and bills against projects.

This module does **not** own user authentication or permissions (that's `users/`), billing rate calculations, or time entry logic. The link between an employee and a user account is a nullable `employee_id` FK on the `users` table — not managed here.

---

## Non-obvious behavior

**`display_name` is unique and NOT NULL, but auto-derived on insert.** If omitted from `POST /employees/`, the service generates `"{first_name} {last_name}"` and appends `" 2"`, `" 3"`, ... on collision via a single `LIKE`-range query (`generate_unique_display_name` in `service.py`). If explicitly supplied, a collision returns 422 — no auto-dedup. Managers can PATCH it to a nickname at any time. Seed helpers that insert `Employee` rows directly (e.g., in tests) must set `display_name` explicitly — the DB NOT NULL constraint rejects rows without it.

**`email` is unique (nullable).** Multiple NULLs are allowed (SQLite treats each NULL as distinct). Only non-null emails are checked for duplicates. The uniqueness guard is application-layer; `POST` and `PATCH` both run `_ensure_email_unique` before committing.

**`EmployeeRole` is time-bound.** Each role record carries `start_date` and `end_date`. The time entry service validates that the referenced `employee_role_id` was active on `start_datetime.date()` at the moment of insert. If the role was not active on that date, the insert is rejected. This validation is application-layer only — the DB has no constraint enforcing it.

**Date-overlap validation is application-layer only.** Two `EmployeeRole` rows for the same employee can have overlapping date ranges if inserted without going through the validation service. Never insert `EmployeeRole` rows directly via raw SQL or seed scripts without checking for overlap first.

**`employee_id` on `users` is nullable.** Not every user is a field employee (e.g., office coordinators may have logins but no employee record), and not every employee has a system login. The join is optional in both directions.

**`EmployeeRoleType` is an admin-managed DB table** (`employee_role_types`), not a `StrEnum`. Admins can add new types at runtime via `POST /employee-role-types/`. The 10 original NYC DOE certification strings were seeded as rows in the initial migration. `EmployeeRole.role_type_id` is a FK into this table; overlap validation compares `role_type_id` values, not strings.

**`EmployeeRoleType` (StrEnum) in `app/common/enums.py`** is a separate, unrelated type used by `SampleTypeRequiredRole` in the lab results module. Do not conflate the two.

---

## Before you modify

- **Adding/renaming a role type**: Use the admin API (`POST /employee-role-types/`). No code change or migration needed.
- **Deleting a role type**: Blocked with 409 if any `employee_roles` rows reference it — delete those roles first.
- **Role date-overlap logic** lives in the router (`create_employee_role`). Overlap is checked per `role_type_id`. Any direct DB insert that bypasses the API must check for overlap manually.
- **Tests**: run `pytest tests/ -v -k employees` after changes to role date logic.
