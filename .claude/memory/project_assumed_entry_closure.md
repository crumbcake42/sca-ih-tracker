---
name: Assumed time entries should block project closure
description: Design gap — assumed time entries are not currently treated as blocking issues for closure, but should be
type: project
originSessionId: ad05f5b7-2320-43d4-b2de-4dd5dc2d564d
---
In `test_project_closure.py`, `test_close_locks_time_entries` seeds an `assumed` time entry and verifies it gets locked on close. But an `assumed` entry means the times haven't been confirmed from daily logs — closing a project with unconfirmed entries is likely wrong.

**Why:** Assumed entries are placeholders; locking them without confirmation silently buries unresolved data quality issues.

**How to apply:** Revisit `lock_project_records` (and possibly `derive_project_status`) to check whether any `assumed` time entries on the project should raise a 409 or be surfaced as a blocking issue before closure is allowed. The current `unconfirmed_time_entry_count` field in `ProjectStatusRead` already tracks this — closing when that count > 0 may need to be blocked.
