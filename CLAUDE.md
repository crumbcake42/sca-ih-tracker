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

### Cross-cutting rule

When a backend endpoint changes shape (new field, removed field, changed status code), add a note to `frontend/HANDOFF.md` so the next frontend session picks it up.
