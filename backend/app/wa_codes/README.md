## Purpose

Owns WA code definitions: the `WACode` table, which stores the code string (e.g., `LAMP30`), a human-readable description, a level (`project` or `building`), and an optional default fee.

This module does **not** own work authorization records, RFAs, or code-to-project assignments. Those belong to `work_auths/`. A `WACode` row is static reference data — it defines what a code *is*; `work_auths/` tracks whether a specific code has been authorized for a specific project.

---

## Non-obvious behavior

**`WACodeLevel` has hard downstream consequences.** The `level` field (`project` or `building`) is not cosmetic — it gates which endpoints accept a code:

- A `building`-level code is rejected with 422 on `POST /work-auths/{id}/project-codes`.
- A `project`-level code is rejected with 422 on `POST /work-auths/{id}/building-codes`.

This same distinction controls deliverable row granularity: project-level codes trigger one `ProjectDeliverable` row per project; building-level codes trigger one `ProjectBuildingDeliverable` row per linked school. Setting the wrong level on a new code will silently produce the wrong deliverable structure.

**`WACodeLevel` values are `"project"` and `"building"`** (lowercase strings via `StrEnum`). The DB stores the string value directly.

**`default_fee` is nullable.** It is a convenience pre-fill for the WA code entry UI, not a constraint. The actual fee is stored on `work_auth_project_codes.fee` and `work_auth_building_codes.budget`.

---

## Before you modify

- **Changing a code's `level`** after it has been assigned to any WA will produce inconsistent data — existing `work_auth_project_codes` or `work_auth_building_codes` rows will have the wrong level. Treat `level` as immutable once a code is in use.
- **Adding new codes** requires re-evaluating `deliverable_wa_code_triggers` seed data in `app/scripts/db.py` to determine whether the new code should auto-create deliverable rows when added to a project.
- **Deleting a code** is blocked by `ondelete="RESTRICT"` on all FK references from `work_auth_project_codes`, `work_auth_building_codes`, `rfa_project_codes`, `rfa_building_codes`, `sample_type_wa_codes`, and `deliverable_wa_code_triggers`. A code in use cannot be deleted at the DB level.
