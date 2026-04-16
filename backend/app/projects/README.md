## Purpose

Owns the `Project` model and all project-scoped relationship tables: `project_school_links`, `ProjectContractorLink`, `ProjectHygienistLink`, and `ProjectManagerAssignment`.

This module does **not** own time entries, lab results, work authorizations, or deliverable status rows. It owns the project record itself and the structural relationships that define which schools, contractors, hygienists, and managers are associated with a project.

---

## Non-obvious behavior

**Link tables are managed via project endpoints — not standalone routers.** Schools, contractors, hygienists, and managers are attached to a project through endpoints on the `/projects/` router. Do not create separate CRUD routers for `project_school_links` or `ProjectContractorLink`. Mutations to those tables happen only as a side effect of project-level operations.

**`project_school_links` is a plain association table, not a model class.** It has no ORM class; it is defined as a `Table` object and used directly in the `Project.schools` many-to-many relationship. Do not add columns to it — if you need metadata on the school-project relationship, that belongs in a separate model.

**`ProjectContractorLink` has an `is_current` flag.** A project can have multiple contractor assignments over time; `is_current=True` identifies the active contractor. There is no DB constraint enforcing that only one row per project has `is_current=True` — this is maintained at the application layer.

**`ProjectManagerAssignment` is an append-only audit trail, not a standard join table.** It records the full history of manager assignments with `assigned_at`, `unassigned_at`, and `assigned_by`. `AuditMixin` is intentionally **not** applied — the table is itself the audit record. The `Project.active_manager` property returns the assignment with `unassigned_at IS NULL`.

**`project_number` has a regex format constraint** (`^\d{2}-\d{3}-\d{4}$`, e.g., `24-001-0001`). Validation is applied at the router layer. The first two digits encode the year; the middle three encode work type. Utility functions for parsing meaning from a project number belong in `common/validators.py` (not yet implemented).

**`get_blocking_notes_for_project(project_id, db)`** (Phase 3.6, in `services.py`) aggregates all unresolved blocking top-level notes across the project itself, its time entries, its deliverables, and its sample batches. Returns `list[BlockingIssue]` (schema in `app/notes/schemas.py`). Two caveats: (1) deliverable notes use the deliverable template's `id` as `entity_id` — a note on template #5 surfaces for any project with that deliverable; (2) sample batches with `time_entry_id=NULL` are excluded because they have no project association. Called by Phase 6's `lock_project_records` and `derive_project_status`.

**`GET /projects/{id}/blocking-issues`** (Phase 3.6, in `app/projects/router/base.py`) is a thin endpoint that calls `get_blocking_notes_for_project()` and returns `list[BlockingIssue]`. It is wired here rather than in the notes module because the aggregation logic spans multiple project-owned entities.

**`derive_project_status()` does not exist yet (Phase 6).** Project status is currently a manually managed field. When Phase 6 is implemented, `derive_project_status(project_id)` will be a pure function with no side effects. Do not cache its result on a `computed_status` column until that function is finalized.

---

## Before you modify

- **`project_school_links`** is referenced by composite FKs in `time_entries`, `work_auth_building_codes`, `rfa_building_codes`, and `project_building_deliverables`. A school cannot be unlinked from a project if any of those dependent rows exist (`ondelete="RESTRICT"`).
- **`AuditMixin` exclusions**: `project_school_links`, `ProjectContractorLink`, and `ProjectHygienistLink` do not use `AuditMixin` — their parent project's audit covers them. `ProjectManagerAssignment` is its own audit trail. See `CLAUDE.md` for the full exclusion list.
- **Tests**: any test that creates a `TimeEntry`, `WorkAuthBuildingCode`, or `ProjectBuildingDeliverable` must first link the school to the project via `project_school_links` or the insert will fail the composite FK constraint.
