# Session Handoff — 2026-04-26

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Phase 6.5 Session B complete.** `WACodeRequirementTrigger` model, admin CRUD (`/requirement-triggers/`), `dispatch_requirement_event` entry point, and event-subscription registry extension are all live. 32 new tests, all green. Full suite: 593 passing.

**Next: Session C — Silo 1: `project_document_requirements`.** See ROADMAP.md Phase 6.5 Session C.

---

## What Was Done This Session

### Phase 6.5 Session B — trigger config + dispatch

**Files created:**
- `app/project_requirements/models.py` — `WACodeRequirementTrigger` model (`wa_code_id`, `requirement_type_name`, `template_params` JSON, `template_params_hash` String(64), `AuditMixin`); unique on `(wa_code_id, requirement_type_name, template_params_hash)`
- `app/project_requirements/services.py` — `hash_template_params(params) -> str` (sha256 of canonical JSON); `dispatch_requirement_event(project_id, event, payload, db)` — routes to registered handlers subscribed to that event
- `app/project_requirements/router.py` — admin CRUD at `/requirement-triggers/`; POST (body includes `wa_code_id`), GET (optional `?wa_code_id=` filter), DELETE `/{trigger_id}`; validates `requirement_type_name` against registry → 422; detects duplicates via hash → 409; `PROJECT_EDIT` permission on writes
- `app/project_requirements/tests/test_models.py` — 6 model tests: round-trip, unique constraint, boundary cases
- `app/project_requirements/tests/test_hash.py` — 8 tests: hash determinism, key-order independence, list-order sensitivity
- `app/project_requirements/tests/test_dispatch.py` — 5 tests: subscribed handler called, unsubscribed skipped, noop on no subscribers, multiple handlers, exception propagates
- `app/project_requirements/tests/test_router.py` — 13 tests: full CRUD coverage incl. duplicate hash detection, unauthenticated rejection

**Files modified:**
- `app/project_requirements/registry.py` — `RequirementTypeRegistry` extended: `_events: dict[RequirementEvent, list[type]]`, `register()` now accepts `events` list, `handlers_for_event(event)` added, `clear()` also clears `_events`; `register_requirement_type(name, events=None)` decorator updated; existing deliverable adapters unaffected (events defaults to `None`)
- `app/project_requirements/schemas.py` — added `WACodeRequirementTriggerCreate` (with `wa_code_id`) and `WACodeRequirementTriggerRead`
- `app/main.py` — added `import app.project_requirements` (populates registry on startup) and `app.include_router(requirement_triggers_router)`
- `backend/ROADMAP.md` — added locked decisions #11 (module ownership) and #12 (reverse inference flow + WA code selection rule); corrected Session B bullet (module path, URL shape)

### Key decisions locked this session

- **Module ownership (Decision #11):** `WACodeRequirementTrigger` lives in `app/project_requirements/`, not `app/wa_codes/`. The table is load-bearing for both forward dispatch and future reverse inference; putting it in `wa_codes` would create a circular dependency.
- **Flat URL `/requirement-triggers/`:** Router owns its own namespace in `main.py`. Nested URL `/wa-codes/{id}/requirement-triggers` was rejected because it would require cross-module router inclusion (`wa_codes/__init__.py` importing from `project_requirements`) — a pattern violation.
- **Module router boundary:** Each module's `router/__init__.py` only composes routers from within that module. Cross-module router inclusion is not allowed — if a new endpoint's URL appears to belong to another module's prefix, the fix is to choose a different URL, not to import the foreign router. All top-level router registration happens in `app/main.py`. Violation that was caught and reverted this session: an early draft put `app/project_requirements/router.py` inside `app/wa_codes/router/__init__.py` because the URL started with `/wa-codes/`. Correct fix was a flat URL (`/requirement-triggers/`) registered directly in `main.py`.
- **Reverse inference flow (Decision #12, deferred):** When a requirement is fulfilled, the system infers which WA code to add (lexicographically smallest `code` among candidates). Needs a new `RequirementEvent` value and a handler in `project_requirements` calling into `work_auths`. Documented but not implemented.
- **Dispatcher error policy:** Fail loud — first raising handler aborts dispatch; caller owns the transaction.
- **Event subscription:** Handlers declare `events=[...]` in `@register_requirement_type(name, events=[...])` decorator. Single `handle_event(project_id, event, payload, db)` classmethod per handler.

### Migration needed (user generates)

New table: `wa_code_requirement_triggers`

```sql
CREATE TABLE wa_code_requirement_triggers (
    id INTEGER PRIMARY KEY,
    wa_code_id INTEGER NOT NULL REFERENCES wa_codes(id) ON DELETE CASCADE,
    requirement_type_name VARCHAR NOT NULL,
    template_params JSON NOT NULL,
    template_params_hash VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT uq_wa_code_requirement_trigger
        UNIQUE (wa_code_id, requirement_type_name, template_params_hash)
);
CREATE INDEX ix_wa_code_requirement_triggers_wa_code_id
    ON wa_code_requirement_triggers (wa_code_id);
```

---

## Next Steps — Session C scope

**Implement Silo 1: `project_document_requirements`.**

Per ROADMAP.md Phase 6.5 Session C:
- `app/required_docs/` module scaffold
- `DocumentType` enum in `app/common/enums.py`
- Model + schema + router + service for `project_document_requirements`
- `TIME_ENTRY_CREATED` event handler: auto-creates `DAILY_LOG` row when employee role's `requires_daily_log=True`
- Register adapter in `app/project_requirements/adapters/`
- Role-type schema: add `requires_daily_log: bool` (admin-toggleable)
- `time_entries.status` gains `EXPECTED` value

---

## Test seed migration (parallel track)

Carried over. 13 test files still use local `_seed_*` helpers (see Session A HANDOFF for full list). Two known-broken files need debugging before migration:
- `app/notes/tests/test_notes_router.py`
- `app/projects/tests/test_hygienist_links.py`

---

## Frontend cross-side notes

Nothing for FE until Session F. After Session F lands, regen the OpenAPI client — new schemas include `WACodeRequirementTriggerCreate`, `WACodeRequirementTriggerRead`, plus Session C–E silo schemas.
