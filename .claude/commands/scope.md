Scope a new unit of work. Propose branch + delegation + HANDOFF stub. **Propose only — no destructive ops without explicit user confirmation in the same turn.**

The user will give you a brief description of what they want to do. Output a structured proposal:

## 1. Side(s) touched

`FE`, `BE`, or `cross-side`. Justify in one sentence (which directories will likely change).

## 2. Proposed branch name

Follow existing repo convention:

| Branch prefix | Use for |
|---|---|
| `be/feat/<topic>` | Backend feature (new endpoint, new schema, new service capability) |
| `be/refactor/<topic>` | Backend refactor (rename, restructure, no behavior change) |
| `fe/feature/<topic>` | Frontend feature (new screen, new component, OpenAPI client wiring) |
| `feat/<topic>` | Cross-side / coordinator-led work that touches both trees |

`<topic>` is kebab-case, ≤ 5 words, descriptive of the deliverable.

If a branch by that name already exists locally, propose a `-v2` suffix or ask the user to pick.

## 3. Delegation recommendation

- **Subagent** (`Agent` tool with `subagent_type: frontend-dev` or `backend-dev`) — for short, self-contained tasks where the user doesn't need to steer mid-flight (≤ ~3 files touched, no UI iteration, no architectural decisions).
- **Dedicated session** (user opens new pane: `tracker-fe` or `tracker-be`) — for multi-turn interactive work, UI iteration, or anything where the dev role needs to ask the user clarifying questions in real time.

Recommend one with one-sentence reasoning.

## 4. HANDOFF stub

Draft the markdown block that, on user confirmation, gets appended to `frontend/HANDOFF.md` or `backend/HANDOFF.md` (or both for cross-side):

```markdown
## YYYY-MM-DD — Coordinator queued: <topic>

**Scope:** <one-line bound on what's in / out>

**Files likely to touch:**
- <path>
- <path>

**Gotchas / non-obvious:** <one or two bullets, or "none">

**Acceptance:** <one-line "done when …">
```

## 5. Draft commit-header

`Phase X.Y Session Z: <topic>` — propose phase/session numbers by reading the most recent existing entry in the relevant `HANDOFF.md` and incrementing the session letter (or proposing the next phase if the user signals a phase boundary). Ask the user to confirm.

## Confirmation gates

Before you actually do anything destructive, ask the user to OK each step explicitly:

1. **Append HANDOFF stub to the relevant `HANDOFF.md`?** (only after OK)
2. **`git checkout -b <branch>` now, or stay on the current branch?** (only after OK; never `git checkout` without confirmation)

Never run `git push` or any operation that affects the remote during `/scope`.
