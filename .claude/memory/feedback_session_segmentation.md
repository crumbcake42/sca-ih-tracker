---
name: Handle each building step in its own session
description: User prefers to split implementation work across multiple sessions — planning/doc-updates in one, each code-building step in its own — rather than a single long session that plans and implements in one go
type: feedback
originSessionId: a90755f4-bab9-48f6-a220-2f16cba4af16
---
When a plan spans multiple implementable steps (new modules, migrations, route work, tests), do not implement them all in the same session as the planning work. When the user approves a plan, the next action is usually to update `data/roadmap.md` and `data/handoff.md` only, and stop. Each building step runs in its own later session.

**Why:** The user wants focused, reviewable work chunks and tight control over what lands in the repo at once. Long sessions that plan + write schema + write routes + write tests make review painful and blur the line between "agreed design" and "written code." Explicitly stated during the required-documents feature planning: "I want to handle each building step in its own session."

**How to apply:** After a plan is approved, if the user doesn't say otherwise, scope the current session to updating `data/roadmap.md` and `data/handoff.md` only (plus memory). Do not create new modules, models, migrations, endpoints, or tests in the same session as the plan. Surface the step list in the handoff so the next session has a clear pick-up point. If a plan section is flagged "not finalized" or "revisit," never implement it without a follow-up design session.
