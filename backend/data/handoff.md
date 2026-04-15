# Session Handoff — 2026-04-15 (Phase 3.6 Session B complete)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**324 tests passing.** Phase 3.6 **Session B** (notes service layer) is complete. The notes migration has been applied. Three service functions are implemented and tested: `create_system_note`, `auto_resolve_system_notes` (in `app/notes/service.py`), and `get_blocking_notes_for_project` (in `app/projects/services.py`).

---

## What Was Done This Session

### Phase 3.6 Session B — Notes service layer

- **Created** `app/notes/service.py`:
  - `create_system_note(entity_type, entity_id, note_type, body, db)` — inserts a blocking note with `created_by_id = SYSTEM_USER_ID`; de-duplicated on `(entity_type, entity_id, note_type)` for unresolved notes.
  - `auto_resolve_system_notes(entity_type, entity_id, note_type, db)` — resolves all matching unresolved notes; returns count.
- **Added** `get_blocking_notes_for_project(project_id, db)` to `app/projects/services.py` — aggregates unresolved blocking notes across the project, its time entries, deliverables, and sample batches; returns `list[BlockingIssue]`.
- **Added** `BlockingIssue` Pydantic schema to `app/notes/schemas.py` (fields: `note_id`, `entity_type`, `entity_id`, `body`, `entity_label`, `link`).
- **Created** `app/notes/tests/test_notes_service.py` — 8 tests for `create_system_note` and `auto_resolve_system_notes`.
- **Created** `app/projects/tests/test_projects_service.py` — 9 tests for `get_blocking_notes_for_project`.

All 324 tests pass.

---

## Design Decisions Made This Session

### `auto_resolve_system_notes` takes `entity_type`

The roadmap signature omitted `entity_type`. Without it, resolving by `(entity_id, note_type)` alone could accidentally resolve notes on different entity types that share the same `entity_id`. Added `entity_type` as a required parameter for precision.

### Deliverable `entity_id` is the template's `deliverable_id`

`project_deliverables` and `project_building_deliverables` have no surrogate ID. Notes on deliverables attach to the `deliverable_id` (template row). A note on template #5 will appear in `get_blocking_notes_for_project` for any project that has deliverable #5. This is a known limitation — revisit if surrogate IDs are added to the deliverable instance tables.

### Batches without a `time_entry_id` are excluded from `get_blocking_notes_for_project`

`sample_batches.time_entry_id` is nullable (Phase 4). A batch with no time entry has no project association. Only batches reachable via `time_entries.project_id` are included.

---

## Phase 3.6 Session Breakdown (ongoing)

- **Session A — Data model:** ✓ COMPLETE
- **Session B — Service layer:** ✓ COMPLETE
- **Session C — Endpoints:** `GET/POST /notes/{entity_type}/{entity_id}`, `POST /notes/{id}/reply`, `PATCH /notes/{id}/resolve`, `GET /projects/{id}/blocking-issues`; API tests covering reply-depth rule and system-note resolve rejection.
- **Session D — Integration:** wire `create_system_note` into any service paths that should emit system notes (primary candidate: deliverable status-transition gate on blocking notes).

---

## Non-Obvious Technical Patterns (carried forward)

### Self-referential relationship with `remote_side`

For a one-to-many self-ref (parent → children) where the FK lives on the child, set `remote_side="Model.id"` on the `parent` relationship, and pair it with a reciprocal `back_populates`-linked collection on the parent. Getting `remote_side` pointed at the wrong column yields a silently-wrong relationship that loads nothing or loops.

### Recursive Pydantic schemas need `model_rebuild()`

`NoteRead` references itself via `replies: list["NoteRead"] = []`. Pydantic v2 requires an explicit `NoteRead.model_rebuild()` after the class definition for the self-reference to resolve.

### Polymorphic attachment — no DB-level FK

`notes.entity_id` has no FK. Service layer validates entity existence before insert. Deleting the parent entity does not cascade to its notes — that is explicitly app-layer (or deferred) cleanup.

### Existing patterns still in force

See `data/handoff.md` history and `app/PATTERNS.md`: `db.get()` vs `select() + populate_existing`, FK validation in early-return paths, `PermissionChecker` returns the user, audit-field test pattern, user-managed migrations, `lazy="selectin"` on serialized relationships, SQLite `Numeric` cast via `Decimal(str(value))`.

---

## Next Step

**Session C:** implement the four notes endpoints and their API tests.

- `GET /notes/{entity_type}/{entity_id}` — threaded list
- `POST /notes/{entity_type}/{entity_id}` — create user note (validates entity exists)
- `POST /notes/{note_id}/reply` — add reply to top-level note (reject reply-to-reply)
- `PATCH /notes/{note_id}/resolve` — resolve user-authored blocking note; 422 on system notes
- `GET /projects/{id}/blocking-issues` — calls `get_blocking_notes_for_project()`

Create `app/notes/router.py` and register it in `app/main.py`. Entity-existence validation needs a helper that looks up the entity by `entity_type` — this lives in `app/notes/service.py`.
