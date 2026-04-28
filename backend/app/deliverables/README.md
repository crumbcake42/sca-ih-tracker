## Purpose

Owns deliverable definitions (`Deliverable`), the trigger config that links WA codes to deliverable auto-creation (`DeliverableWACodeTrigger`), and per-project status rows (`ProjectDeliverable`, `ProjectBuildingDeliverable`).

This module does **not** own project state, WA code definitions, or the logic that determines when a deliverable becomes required. It owns the rows that track whether a specific deliverable has been completed for a specific project or building.

---

## Non-obvious behavior

**`DeliverableWACodeTrigger` is seeded config, not dynamic.** The association between a WA code and a deliverable (i.e., "adding code X to a project should auto-create deliverable Y") is seeded via `app/scripts/db.py`. It is not created at runtime by user actions. When a new deliverable or WA code is added, the seed script must be updated to wire the trigger.

**Two parallel, independent status tracks.** Each deliverable row carries two status fields that evolve independently:

- `InternalDeliverableStatus` — tracks internal preparation state (`incomplete → blocked → in_review → in_revision → completed`). `blocked` requires a `notes` explanation. This is set manually by coordinators.
- `SCADeliverableStatus` — tracks the SCA-facing submission lifecycle (`pending_wa → pending_rfa → outstanding → under_review → rejected → approved`). The first three values are derived from project/WA/code state and will be auto-updated by `recalculate_deliverable_sca_status()` in Phase 5. The last three (`under_review`, `rejected`, `approved`) are set manually.

Do not manually set `pending_wa`, `pending_rfa`, or `outstanding` in service code — Phase 5 will own those transitions.

**`ProjectDeliverable` and `ProjectBuildingDeliverable` are separate tables**, not a single table with a nullable `school_id`. A nullable column in a composite primary key is illegal in PostgreSQL. Project-level deliverables live in `project_deliverables`; building-level deliverables live in `project_building_deliverables`.

**`ProjectBuildingDeliverable` has a composite FK to `project_school_links`.** The `(project_id, school_id)` pair must already exist in `project_school_links` before a building deliverable row can be inserted. The service enforces this with a 422 if the school is not linked to the project.

**Deliverable rows can be created from multiple sources.** A row may be created when a WA code is added (via trigger), when a lab result is recorded, or by manual entry. All are valid. Once a row exists, its `sca_status` is always maintained by the same `recalculate_deliverable_sca_status(project_id)` call regardless of how it was created.

---

## Before you modify

- **Do not manually set `pending_wa`, `pending_rfa`, or `outstanding`** on `sca_status` in service code — these will be managed by `recalculate_deliverable_sca_status()` in Phase 5. Write status transitions for `under_review`, `rejected`, and `approved` only.
- **`Deliverable.level` is immutable after creation.** `PATCH /deliverables/{id}` returns 422 if `level` is included with a different value. This is enforced at the API layer to prevent the inconsistency that would result from changing level after downstream project rows exist.
- **When adding a new deliverable**, check whether it should be wired to any WA codes via `DeliverableWACodeTrigger` and update the seed script accordingly.
- **Deleting a deliverable** — `DELETE /deliverables/{id}` is guarded: `GET /deliverables/{id}/connections` returns reference counts across `project_deliverables`, `project_building_deliverables`, and `deliverable_wa_code_triggers`. The DELETE returns 409 if any count is nonzero. The trigger table FK is `ondelete=CASCADE` at the DB level, but the guard treats any nonzero count as a blocker — force explicit cleanup before deletion.
- **Tests**: the composite FK on `ProjectBuildingDeliverable` means test fixtures must link the school to the project before inserting a building deliverable row.
