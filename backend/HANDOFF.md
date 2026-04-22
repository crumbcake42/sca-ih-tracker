# Session Handoff — 2026-04-22 (Phase 1.6 planned; no code written)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Phase 1.5 complete. Phase 6 complete.** Before proceeding to Phase 6.5, a new **Phase 1.6 — Guarded DELETE and Connections Endpoints** was designed and added to the roadmap. No code was written this session — it was a design session only. Phase 6.5 is on hold until Phase 1.6 is complete.

---

## What Was Done This Session

Designed the guarded DELETE pattern for all thin reference entities and added Phase 1.6 to the roadmap (four sessions: infrastructure, employees, schools/contractors/hygienists, wa_codes/deliverables).

---

## Design Decisions Made This Session

### Guarded DELETE pattern: `_get_references` helper + `assert_deletable`

Each deletable entity gets:

1. A per-entity `_get_{entity}_references(db, id) -> dict[str, int]` function next to its router — checks every table that holds a FK to this entity via `COUNT` queries, returns `{label: count}`.
2. `GET /{entity_id}/connections` — calls the helper, returns the dict. For the frontend delete-confirmation dialog.
3. `DELETE /{entity_id}` — calls the helper independently, then calls `assert_deletable(refs)` from `app/common/guards.py`. Returns 409 `{"blocked_by": [...labels...]}` listing **all** blocking reasons at once (not fail-fast). Returns 204 on success.

### `assert_deletable` lives in `app/common/guards.py`, not inline

It's a thin wrapper: raises `HTTPException(409, {"blocked_by": [...]})` if any count > 0. Kept separate so every DELETE endpoint produces the same 409 shape without duplication.

### Connections endpoint and DELETE guard are always independent

The connections endpoint result is stale by the time DELETE fires (TOCTOU). The DELETE endpoint re-runs the reference checks regardless of what the connections endpoint returned. They share code via the helper, not via HTTP calls.

### `COUNT` queries over `scalar_one_or_none`

Reference checks use `select(func.count()).select_from(...)` — one round-trip regardless of how many rows exist. Fetching a row to check existence is unnecessarily wide.

### DELETE is blocked even when CASCADE is set on the FK

For example, `project_school_links` has `ondelete=CASCADE` on `schools.id`, but the connections endpoint and delete guard still check it. Silently wiping all project-school associations when a school is deleted would be destructive; the guard forces an explicit unlink first.

---

## Next Step

**Phase 1.6 — Session A: Infrastructure.**

- Create `app/common/guards.py` with `assert_deletable(refs: dict[str, int]) -> None`
- Add PATTERNS.md entry **#14 — Guarded DELETE** covering: per-entity `_get_references` helper, `assert_deletable`, TOCTOU note, COUNT vs scalar_one_or_none rationale

After Session A, proceed in order: Session B (employees), Session C (schools/contractors/hygienists), Session D (wa_codes/deliverables). Full session breakdown is in ROADMAP.md under Phase 1.6.

Note: Phase 6.5 has an open design question — **placeholder→actual matching layer is NOT FINALIZED** (see roadmap). That must be revisited before any placeholder promotion logic is implemented when Phase 6.5 resumes.
