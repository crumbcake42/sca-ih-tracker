## Purpose

Owns `Employee` records and time-bound `EmployeeRole` instances. An employee is an operational/billing entity — a person who performs field work and bills against projects.

This module does **not** own user authentication or permissions (that's `users/`), billing rate calculations, or time entry logic. The link between an employee and a user account is a nullable `employee_id` FK on the `users` table — not managed here.

---

## Non-obvious behavior

**`EmployeeRole` is time-bound.** Each role record carries `start_date` and `end_date`. The time entry service validates that the referenced `employee_role_id` was active on `start_datetime.date()` at the moment of insert. If the role was not active on that date, the insert is rejected. This validation is application-layer only — the DB has no constraint enforcing it.

**Date-overlap validation is application-layer only.** Two `EmployeeRole` rows for the same employee can have overlapping date ranges if inserted without going through the validation service. Never insert `EmployeeRole` rows directly via raw SQL or seed scripts without checking for overlap first.

**`employee_id` on `users` is nullable.** Not every user is a field employee (e.g., office coordinators may have logins but no employee record), and not every employee has a system login. The join is optional in both directions.

**`EmployeeRoleType` values are long certification strings**, not short codes. They map directly to NYC DOE certification categories. Do not rename or remove values — existing `employee_roles` rows reference them as stored enum strings.

---

## Before you modify

- **Changes to `EmployeeRoleType`** propagate to `sample_type_required_roles` (lab results config) and the time entry role-validation service. Adding a new value is safe; renaming or removing an existing value requires a data migration of any rows using that value.
- **Role date-overlap logic** lives in the employees service. Any endpoint that creates or patches an `EmployeeRole` must call that validation before committing.
- **Tests**: run `pytest tests/ -v -k employees` after changes to role date logic.
