# SCA IH Tracker

Fullstack project: FastAPI backend + React/Vite frontend.

## Project Map

| Directory   | Stack                                            | Docs                 |
| ----------- | ------------------------------------------------ | -------------------- |
| `backend/`  | FastAPI, SQLAlchemy, SQLite                      | `backend/CLAUDE.md`  |
| `frontend/` | Vite + React + TypeScript, TanStack Router/Query | `frontend/CLAUDE.md` |

Run commands are defined in `justfile` at the project root:

- `just api` — start backend dev server (port 8000)
- `just ui` — start frontend dev server (port 3000)
- `just dev` — start both servers together
- `just test` — run backend tests

## Integration Contract

### API base URL

Backend runs at `http://127.0.0.1:8000`.

### OpenAPI client generation

Frontend generates typed client hooks from the backend's `/openapi.json`. See `frontend/CLAUDE.md` for the exact command. Regenerate whenever a backend endpoint changes shape.

### Auth shape (non-obvious)

`POST /auth/token` uses **OAuth2 password flow** — request body is **form-encoded** (`application/x-www-form-urlencoded`), not JSON. Generated client code often gets this wrong; verify before using the generated login mutation.

### Cross-cutting rules

Prefer inferred or narrowed types over Any (Python) / any / unknown (TypeScript); if generics or known interfaces can express the shape, use them.

When a backend endpoint changes shape (new field, removed field, changed status code), add a note to `frontend/HANDOFF.md` so the next frontend session picks it up.

**Session scope:** Keep each session scoped to one side. During a backend session, do not read `frontend/HANDOFF.md`, `frontend/ROADMAP.md`, or any other frontend doc to plan work — and vice versa. The only exception is at the end of a session: if changes on one side affect the other, write a note to the other side's `HANDOFF.md` so the next session picks it up.

### Coordinator role (when running from the repo root)

When this Claude session runs from the repo root (i.e. *not* inside `frontend/` or `backend/`), you are acting as the **coordinator** of a small team — the user, plus `frontend-dev` and `backend-dev` (defined in `.claude/agents/`). Your job:

- Talk with the user; scope and sequence work; manage cross-side concerns.
- Delegate side-specific code work — short autonomous tasks via the `Agent` tool (`subagent_type: frontend-dev` or `backend-dev`); interactive multi-turn work via a *dedicated session* the user opens with `tracker-fe` / `tracker-be` (which load `/fe-dev` and `/be-dev` respectively).
- Manage branch scope and commit boundaries via `/scope` (start of work) and `/wrap` (end of work).
- Do **not** directly modify files under `frontend/src/` or `backend/app/` yourself. Cross-side or trivial edits (renames, doc-only edits, OpenAPI client regen kicked off via `pnpm dlx`) are fine.

**Session lifecycle (lean, hook-driven):** every session starts with `/brief` and ends with `/note`. `/gmorning` and `/gnight` are reserved for cross-machine work — they sync the in-repo `.claude/memory/` snapshot against your live `~/.claude/` memory and are not for routine session boundaries.

**Active git management:** when the user describes a new unit of work, run `/scope` *before* writing any code or invoking any subagent. When a unit of work is done, run `/wrap` to propose commit boundaries and messages. Never run `git commit`, `git push`, or `git checkout -b` without explicit confirmation in the same turn.
