# Repo-local Claude notes

Snapshot of the plans + memory entries needed to implement the in-flight
backend refactor arc (Phase 6.5 Sessions E0a → E0b → E0c → E0d → {E, E2} → F).
Copied from `~/.claude/` on 2026-04-27 so this context travels with the repo
across machines.

## `plans/`

- `review-the-current-phase-cached-wilkes.md` — produced **Sessions E0a + E0b**
  (module split + Option C router pattern)
- `confirm-you-have-a-transient-bengio.md` — produced **Sessions E0c + E0d**
  (protocol/schema hygiene + drop `is_required` columns); also gutted the
  speculative Phase 6.7 framework
- `i-want-to-revisit-refactored-valley.md` — produced **Session E2** (Silo 4
  `lab_reports`; retires `SampleBatch.is_report`)

## `memory/`

Refactor-relevant feedback / project memories:

- `feedback_module_organization.md` — contract layer in `app/common/`; child
  modules never declare parent URL prefix (drives E0a)
- `feedback_router_patterns.md` — Option C two-router-per-file pattern, async
  SQLAlchemy gotchas (drives E0b)
- `feedback_lateral_vs_hierarchical.md` — two-layer rule for peer
  navigation; peer-route factory deferred until 8+ uniform edges
- `feedback_schema_scoping.md` — only add columns that drive logic
  (justification for retiring `is_report`)
- `feedback_session_segmentation.md` — handle each building step in its own
  session; after plan approval, scope to ROADMAP/HANDOFF updates only
- `feedback_session_scope.md` — keep session context scoped to the active
  side (backend/ vs frontend/); cross over only at session end via HANDOFF
- `project_assumed_entry_closure.md` — assumed time entries should probably
  block closure; revisit `lock_project_records`

## How this is used

The authoritative copies live in `~/.claude/` on the original machine. This
folder is a point-in-time snapshot for cross-machine continuity during the
refactor — once Sessions E0a–F + E2 land, these can be deleted (or refreshed
from `~/.claude/` again if more sessions accumulate context).
