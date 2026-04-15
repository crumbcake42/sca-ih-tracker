## Purpose

Owns the `notes` table: a polymorphic threaded-note store that attaches to any
business entity (`project`, `time_entry`, `deliverable`, `sample_batch`). Supports
both user-authored notes and system-generated notes (`note_type IS NOT NULL`),
and a single level of replies.

This module does **not** own: the services that emit system notes (those live in
the module whose condition triggered the note — e.g. deliverable status
transitions), and does not own the project-level aggregation query
(`get_blocking_notes_for_project()` lives in `app/projects/service.py`).

---

## Non-obvious behavior

**Polymorphic reference — no DB-level FK on `entity_id`.** A single `notes`
table can attach to any entity type. Referential integrity is enforced at the
service layer: before creating a note, the service must verify the target
entity exists. Deleting the parent entity does not cascade to its notes — that
cleanup is also app-layer (or deferred, since notes are mostly informational).

**One reply level only.** `parent_note_id` is a self-referential FK, but the
service/schema layer rejects replies to replies. Enforce at POST
`/notes/{id}/reply` by checking `parent.parent_note_id IS NULL`. Replies are
never `is_blocking=True`; only top-level notes can block.

**System vs. user notes.** `note_type IS NOT NULL` identifies a system note.
System notes:

- Are created via `create_system_note()` with `created_by_id = SYSTEM_USER_ID`
- Are de-duplicated: `create_system_note` checks for an existing unresolved
  note of the same `(entity_type, entity_id, note_type)` before inserting
- **Cannot be manually resolved.** They auto-resolve via
  `auto_resolve_system_notes(entity_id, note_type)` when the underlying
  condition clears. The resolve endpoint returns 422 on a system note.

**Resolution of user-authored blocking notes.** `PATCH /notes/{id}/resolve`
requires a `resolution_note` in the body. The service sets `is_resolved=True`,
`resolved_by_id`, `resolved_at`, **and** auto-appends the `resolution_note` as
a reply — preserving rationale in the thread.

**`@mention` support is intentionally not parsed.** Bodies are stored as-is
(no sanitization, no stripping). A future mention parser can extract
`@username` patterns without a data migration.

---

## Before you modify

- **Adding a new `NoteEntityType` value** is cheap schema-wise (string column),
  but requires updating `get_blocking_notes_for_project()` to include the new
  entity in its aggregation, and the service's entity-existence check.
- **Adding a new `NoteType` value** requires a paired `create_system_note`
  caller and a paired `auto_resolve_system_notes` caller — otherwise the note
  will be created and never clear.
- **Do not add a generic `resolve` path for system notes.** If a condition
  needs manual override, add a dedicated endpoint on the owning entity, not a
  resolve-any-note hatch.
