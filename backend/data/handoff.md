# Session Handoff — 2026-04-15 (Phase 6.5 design session; no code written)

This file captures decisions made and work completed in the most recent session. Read before continuing.

---

## Where Things Stand

**307 tests passing (unchanged from last session). Phase 4 migration still pending. No code was written this session — it was a design session for Phase 6.5 (Required Documents and Expected/Placeholder Entities).**

The full Phase 6.5 design now lives in `data/roadmap.md` (Phase 6.5 section) with the exhaustive plan at `.claude/plans/witty-brewing-bentley.md`. Read the roadmap section first; crack the plan only when implementing.

---

## What Was Done This Session

Design-only, no code. Agreed with the user:

- **New Phase 6.5** inserted between Phase 6 (closure) and Phase 7 (dashboards)
- Three silos for required documents: `project_document_requirements` (generic on/off: daily logs, re-occupancy letters, minor letters), `contractor_payment_records` (CPR with its own RFA+RFP sub-flow), `dep_filing_forms` + `project_dep_filings` (DEP package)
- Cross-cutting **expected/placeholder pattern**: `is_placeholder` bit + nullable identity columns on derived-entity tables; `TimeEntryStatus.EXPECTED` joins the existing `assumed`/`entered`/`locked`; `wa_code_expected_entities` config table drives auto-derivation from WA codes; project templates are a deferred convenience layer on top
- **Dismissibility generalized** (supersedes the Phase 4 "dismissable requirements" idea, which is rolled into Phase 6.5): every required thing can be satisfied or dismissed via a dedicated endpoint that requires `dismissal_reason`; closure aggregator only checks `is_required=True AND not_satisfied`
- **CPR history via system notes, not a history table**: on re-submission or stage regression, service writes a `create_system_note()` capturing prior dates before clearing them. No `contractor_payment_record_history` table
- File upload infrastructure deferred indefinitely. `is_saved=true, file_id=null` is a permanently valid state meaning "on file outside the system"

---

## Open Design Risks — Revisit Before Implementation

### ⚠️ Placeholder→actual matching layer — NOT FINALIZED

The service logic that promotes a placeholder row when a matching real entity arrives (a manager creates a real time entry that fulfills an `EXPECTED` placeholder, etc.) has only a sketch in the plan file. **Do not write this code without a dedicated design session.** The sketch is directional only — covers the dedupe key and a candidate match-first-by-role rule, but the user explicitly flagged this for revisit.

### Expected time entries vs existing status invariants

`TimeEntryStatus.EXPECTED` (new) must not collide with `ASSUMED` (system-created placeholder for daily-log backfill). They have different meanings:

- `ASSUMED`: employee known, date known, midnight-to-midnight span, awaiting manager confirmation
- `EXPECTED`: employee/date/span all unknown; placeholder for "someone with role X will eventually do this work"

Review overlap checks, locked-project guards, and the `assumed → entered` flip rule for interactions with `EXPECTED` before writing.

---

## Phase 4 Migration Still Pending

(Unchanged from last session — included here because implementation of any Phase 6.5 work will need this migration applied first.)

**Migration label:** `add_status_enums_nullable_batch_time_entry`

**Three schema changes in one migration:**

1. `ALTER TABLE time_entries ADD COLUMN status VARCHAR NOT NULL DEFAULT 'entered'`
2. `ALTER TABLE sample_batches ADD COLUMN status VARCHAR NOT NULL DEFAULT 'active'`
3. Make `sample_batches.time_entry_id` nullable (SQLite: recreate table)

---

## What Was Done This Session

### Documentation pass — module READMEs written

Nine `README.md` files were created across the project. Each follows the three-section format from `data/roadmap.md`: **Purpose**, **Non-obvious behavior**, **Before you modify**. Mermaid diagrams are embedded in modules with state machines or validation chains.

| File                         | Key content                                                                                                                            |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `app/employees/README.md`    | Time-bound EmployeeRole, app-layer overlap validation, nullable user link                                                              |
| `app/users/README.md`        | PermissionChecker returns the user, SYSTEM_USER_ID=1 is reserved, RBAC structure                                                       |
| `app/wa_codes/README.md`     | WACodeLevel drives endpoint gating + deliverable granularity; treat level as immutable once in use                                     |
| `app/deliverables/README.md` | Dual independent status tracks, trigger config is seeded not dynamic, separate project/building tables                                 |
| `app/common/README.md`       | AuditMixin is explicit-only, SYSTEM_USER_ID import location, router factory functions                                                  |
| `app/work_auths/README.md`   | WA code status state machine (Mermaid), RFA state machine (Mermaid), one-pending-RFA-per-WA rule                                       |
| `app/projects/README.md`     | Link tables via project endpoints only, ProjectManagerAssignment is append-only audit trail, composite FK dependencies                 |
| `app/time_entries/README.md` | Planned state diagram (Mermaid, status col not yet added), overlap → system notes not 422, SYSTEM_USER_ID identifies quick-add entries |
| `app/lab_results/README.md`  | Config vs data layer, batch validation chain flowchart (Mermaid), sample_unit_type validation is app-layer only                        |

The roadmap's "Files to generate" checklist was updated. Still unchecked: `backend/README.md`, `backend/app/PATTERNS.md` (already exists), `backend/app/notes/README.md` (blocked until Phase 3.6 implements the notes module).

Thin CRUD modules (schools, contractors, hygienists) were deliberately skipped per the roadmap's own rule.

---

---

## Design Decisions (permanent — carry forward)

### `time_entries.source` — DROPPED

The planned `source` column (`manual` | `system`) is redundant. `created_by_id == SYSTEM_USER_ID` already encodes whether an entry was system-created. Do not add this column.

### `conflicted` status — DROPPED

The planned `conflicted` status value and `flag_employee_overlaps` service are removed. The original intent was to detect when two time entries for the same employee overlap and block project closure until resolved.

**Why dropped:** Maintaining `conflicted` as running state requires re-evaluating overlap on every create, update, and delete — querying all entries for an employee, updating flags, and coordinating with the `locked` transition. It's complex, easy to get wrong, and turns a minor data-entry mistake into a hard project-closure block for a small internal team.

**Replacement:** Validate at insert/update time. If the new/updated entry's time span overlaps an existing entry for the same employee, return 422 with a clear message identifying the conflict. No `conflicted` status. No reactive service. The error appears at the point of entry, not later as a blocking flag on the project.

### `orphaned` batch status + `orphan_detached_batches` — DROPPED

The planned `orphaned` status value and `orphan_detached_batches` service (which would mark batches orphaned when their time entry was deleted or its span changed past the collection date) are removed.

**Why dropped:** Time entries are rarely deleted in practice — they're logs of work done. The scenario that triggers orphaning (modifying a time entry's date range far enough that the collection date no longer falls within it) is an edge case not described in the original requirements.

**Replacement:** Block deletion of `time_entries` that have `active` or `discarded` batches with a 409 ("this entry has X batches linked to it — reassign or delete them first"). No orphan state to manage.

### Revised state models

**`time_entries.status`** (3 values, down from 4):

- `assumed` — system placeholder; times not yet confirmed from daily logs
- `entered` — times manually input or confirmed by a manager
- `locked` — project closed; read-only

When a manager edits a `status=assumed` entry: `status → entered`. `created_by_id` stays as `SYSTEM_USER_ID`. `updated_by_id` = manager's ID.

**`sample_batches.status`** (3 values, down from 4):

- `active` — normal
- `discarded` — invalidated by manager
- `locked` — project closed; read-only

### NULL end_datetime — assumed entries only

`end_datetime` being NULL is valid only on `assumed` entries. These are always created with `start_datetime = 00:00:00` of the work date. For overlap checking, treat NULL end_datetime as midnight of the next day (`DATETIME(start_datetime, '+1 day')`), which works correctly because start is always at midnight.

### Dismissable requirements — ROLLED INTO PHASE 6.5

Originally scoped as a Phase 4 follow-up for batches with `time_entry_id=null`. The 2026-04-15 design session generalized this: every required thing (document requirement, CPR, DEP filing, placeholder time entry, etc.) can be **satisfied** (real data arrives) or **dismissed** via a dedicated endpoint that requires a `dismissal_reason`. See Phase 6.5 in `data/roadmap.md`. No separate Phase 4 follow-up work remains on this concept.

### Phase 5 (Observability) — DEFERRED

Deferred until the app is deployed and real performance data is available. Do not implement before Phase 6.

---

## Next Step — Still Phase 3.6 (Notes and Blockers)

Phase sequencing is unchanged by this session's work. Phase 3.6 remains the next thing to build, because both Phase 6 (closure gates) and Phase 6.5 (required docs) depend on the notes infrastructure — CPR auto-notes on re-submission need `create_system_note()` in place.

Phase 3.6 main work (design in `data/roadmap.md`):

1. **`time_entries.status`** — add `TimeEntryStatus` enum (`assumed`, `entered`, `locked`); add nullable column with default `entered` (existing manual entries are already confirmed); add server_default as well so the DB column has a fallback
2. **`sample_batches.status`** — add `SampleBatchStatus` enum (`active`, `discarded`, `locked`); add column with default `active`
3. **`sample_batches.time_entry_id` nullable** — remove `NOT NULL` constraint

**Do not start Phase 6 or 6.5 until Phase 3.6 is complete.**

### Phase 6.5 build sequencing (when we get there)

Each step is its own session:

1. Schema + enums: `app/required_docs/` models (all four tables) + `DocumentType`, `CPRStageStatus` enums + migration
2. `requires_daily_log` on role type + admin toggle
3. `TimeEntryStatus.EXPECTED` + service-layer nullability guards
4. `wa_code_expected_entities` config table + admin CRUD + seed rules
5. `derive_expected_entities_for_project()` — idempotent derivation **(pause here — matching layer design session required before step 6)**
6. Placeholder→actual matching layer (design not yet finalized)
7. CRUD routers per silo + dismissal endpoints (require `dismissal_reason`)
8. Auto-creation hooks: time entry → daily log requirement; project/contractor link → CPR row
9. CPR auto-note service (requires Phase 3.6)
10. Extend Phase 6's `get_blocking_notes_for_project()` to include all three silos

Then: implement `POST /lab-results/batches/quick-add`.

**Do not start Phase 6 until the quick-add endpoint is working and tested.**

---

## Non-Obvious Technical Patterns

### `db.get()` is wrong for GET endpoints that serialize nested relationships

Use `select()` with `.execution_options(populate_existing=True)` instead. Applied in `app/lab_results/service.py`.

### FK validation in service functions that return early

SQLite does not enforce FK constraints by default. Any service function that conditionally returns early must explicitly check that FK targets exist via `db.get(TargetModel, fk_id)`. Applied in `app/lab_results/router/batches.py`.

### `PermissionChecker` returns the user

`PermissionChecker.__call__` returns the user object. Use `current_user: User = Depends(PermissionChecker(X))` to both enforce permissions and capture the user in one dependency — no redundant `get_current_user` call needed.

### Audit field testing pattern

Audit fields (`created_by_id`, `updated_by_id`) are not in any Read schemas, so they can't be checked from response JSON. After an API call via `auth_client`, query `db_session` directly:

```python
obj = await db_session.get(Model, response.json()["id"])
assert obj.created_by_id == 1  # fake_user.id from auth_client fixture
```

Or for an object already in scope, use `await db_session.refresh(obj)` then check the field.

### User-managed migrations

Do not run `alembic` commands. The user generates and applies all migrations themselves.
