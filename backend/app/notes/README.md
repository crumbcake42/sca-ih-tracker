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

- Are created via `create_system_note(entity_type, entity_id, note_type, body, db)`
  with `created_by_id = SYSTEM_USER_ID`
- Are de-duplicated: `create_system_note` checks for an existing unresolved
  note of the same `(entity_type, entity_id, note_type)` before inserting;
  returns the existing note rather than creating a duplicate
- **Cannot be manually resolved.** They auto-resolve via
  `auto_resolve_system_notes(entity_type, entity_id, note_type, db)` when the
  underlying condition clears. `entity_type` is required — omitting it would
  accidentally resolve notes on different entity types that share the same
  `entity_id`. The resolve endpoint returns 422 on a system note.

**`BlockingIssue` schema** (`app/notes/schemas.py`) is the return type of
`get_blocking_notes_for_project()` (which lives in `app/projects/services.py`).
Fields: `note_id`, `entity_type`, `entity_id`, `body`, `entity_label`, `link`.

**Resolution of user-authored blocking notes.** `PATCH /notes/{id}/resolve`
requires a `resolution_note` in the body. The service sets `is_resolved=True`,
`resolved_by_id`, `resolved_at`, **and** auto-appends the `resolution_note` as
a reply — preserving rationale in the thread.

**`@mention` support is intentionally not parsed.** Bodies are stored as-is
(no sanitization, no stripping). A future mention parser can extract
`@username` patterns without a data migration.

---

## Router-level patterns

**Route registration order — reply before create.** `POST /notes/{note_id}/reply` is registered before `POST /notes/{entity_type}/{entity_id}`. Starlette checks routes in registration order and does not auto-prioritise literal path segments over parameters. For `/notes/42/reply` both patterns match structurally; placing the reply route first ensures it wins. For `/notes/project/42` the reply route does not match (second segment is not `"reply"`), so it correctly falls through to the create route.

**`expunge()` + reload for just-created Note objects.** After `await db.commit()` on a newly created Note, expunge the object from the session before re-querying it with nested `selectinload`. Without this, SQLAlchemy sees the `replies` collection as "already present" (uninitialised `InstrumentedList`) and skips the secondary selectin query. FastAPI then accesses the attribute and triggers a synchronous lazy-load → `MissingGreenlet`. Fix: `db.expunge(note)` removes the object from the identity map; the reload query gets a fresh Python object with `replies` in a true unloaded state. `db.expire_all()` is **not** a safe substitute — it disrupts async session state and causes `MissingGreenlet` on subsequent cursor creation.

**Nested `selectinload` for recursive `NoteRead`.** `NoteRead.replies: list["NoteRead"]` is two levels deep. Use `selectinload(Note.replies).selectinload(Note.replies)` in every query that returns Note objects for serialisation. One level is insufficient — the second `selectinload` loads the replies' own `replies` collections (always empty, since one level of nesting is enforced), preventing a lazy-load attempt during serialisation.

**`populate_existing=True` on `list_notes`.** The `GET /notes/{entity_type}/{entity_id}` endpoint uses `populate_existing=True` because notes may be seeded into the session before the query runs (e.g., in tests), and the identity map would otherwise return stale versions.

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
