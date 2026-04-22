# Session Handoff — 2026-04-22 (Phase 1.6 Session C complete)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**Phase 1.6 Session C complete.** Schools, contractors, and hygienists now have connections endpoints and guarded DELETE.

---

## What Was Done This Session

- `app/schools/router/base.py` — added `_get_school_references` (checks `project_school_links`), `GET /schools/{school_id}/connections`, `DELETE /schools/{school_id}` (guarded)
- `app/contractors/router/base.py` — added `_get_contractor_references` (checks `project_contractors_links`), `GET /contractors/{contractor_id}/connections`, `DELETE /contractors/{contractor_id}` (guarded)
- `app/hygienists/router/base.py` — added `_get_hygienist_references` (checks `project_hygienist_links`), `GET /hygienists/{hygienist_id}/connections`, upgraded existing unguarded DELETE to go through `assert_deletable`

**Non-obvious:** The actual contractor link table is named `project_contractors_links` (with an `s` on `contractors`) — the `ProjectContractorLink` ORM class maps to that tablename. Connections response key reflects that: `"project_contractors_links"`.

---

## Next Step

**Phase 1.6 — Session D: wa_codes, deliverables.**

For each entity, add:
- `_get_{entity}_references(db, entity_id)` helper
- `GET /{entity_id}/connections`
- `DELETE /{entity_id}` — guarded

Reference tables to check:
- **WA Codes** — `work_auth_project_codes.wa_code_id`, `work_auth_building_codes.wa_code_id`, `rfa_project_codes.wa_code_id`, `rfa_building_codes.wa_code_id`, `deliverable_wa_code_triggers.wa_code_id`, `sample_type_wa_codes.wa_code_id`
- **Deliverables** — `project_deliverables.deliverable_id`, `project_building_deliverables.deliverable_id`, `deliverable_wa_code_triggers.deliverable_id`

After Session D, Phase 1.6 is complete.

Note: Phase 6.5 has an open design question — **placeholder→actual matching layer is NOT FINALIZED** (see roadmap). That must be revisited before any placeholder promotion logic is implemented when Phase 6.5 resumes.
