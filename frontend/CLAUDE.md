# SCA IH Tracker — Frontend

## Build & Run

- Install: `pnpm install`
- Dev server: `pnpm dev` (port 3000) or `just ui` from project root
- Tests: `pnpm test`
- Lint/format: `pnpm check`
- OpenAPI client generation: `pnpm dlx @hey-api/openapi-ts` (backend must be running at port 8000)

## Documentation: What Goes Where

| File              | Purpose                                                                              |
| ----------------- | ------------------------------------------------------------------------------------ |
| `ROADMAP.md`      | Design intent, stack decisions, non-obvious API behaviors, phase plan                |
| `HANDOFF.md`      | Per-session continuity; what was done last, what's next                              |
| `src/PATTERNS.md` | (create when patterns solidify) Component conventions, query patterns, form patterns |

---

## Non-Obvious Items

Read `ROADMAP.md` fully before building any screen. Key things that the OpenAPI schema will not tell you:

1. **Auth is form-encoded** — `POST /auth/token` uses `application/x-www-form-urlencoded`, not JSON
2. **Project status is derived** — comes from `GET /projects/{id}/status`, not a column; don't build a status column in list views until Phase 7 dashboard endpoints land
3. **Notes are polymorphic** — one `<NotesPanel entityType="…" entityId={…} />` serves all four entity types (`project` | `time_entry` | `deliverable` | `sample_batch`)
4. **Deliverables have two status tracks** — `internal_status` (5 values) and `sca_status` (6 values); first three `sca_status` values are backend-derived and must render read-only
5. **Time entry 422 on overlap** — the form must parse the conflicting `time_entry_id` from the 422 body and offer a link to it, not a generic error toast
6. **Closure returns 409 with blocking issues** — render the `blocking_issues[]` payload inline in the close dialog with deep links, not a generic toast
7. **Quick-add is the primary entry point** — `POST /lab-results/batches/quick-add` creates assumed time entry + sample batch atomically; don't route managers through manual time-entry creation

## UI Conventions

- **Phosphor icons** — use the `*Icon` suffix form: `SignOutIcon`, `FolderOpenIcon`, `UserIcon`, etc. The bare names (`SignOut`, `FolderOpen`) are deprecated.
- **shadcn style is `radix-lyra`** — no `form` component; use `Field` / `FieldLabel` / `FieldError` / `FieldGroup` from `@/components/ui/field` with react-hook-form directly
- **Zod v4 resolver** — use `standardSchemaResolver` from `@hookform/resolvers/standard-schema`, not `zodResolver`

## Architecture Notes

### Three-tier structure

`routes/ → pages/ → features/ → components/, hooks/, fields/, lib/`

- **`src/routes/`** — TanStack Router file-based config only. Route files import their page component from `@/pages/` and nothing else from the app.
- **`src/pages/`** — URL-bound compositions. Use `getRouteApi('/path')` (not `import { Route }`) to access typed search/loader data. Compose from features.
- **`src/features/<domain>/`** — routing-agnostic domain components and API wrappers. Never import from `pages/` or `routes/`.
- **`src/components/`, `src/hooks/`, `src/fields/`, `src/lib/`** — shared, domain-free primitives.

### API wrapper layer

Feature components and pages import `*Options`/`*Mutation`/`*QueryKey` helpers from `@/features/<domain>/api/`, never directly from `@/api/generated/`. Wrappers use domain-owned names (`listSchoolsOptions`, not `listEntriesSchoolsGetOptions`). Add wrappers just-in-time — don't pre-map unused endpoints. `src/auth/store.ts` and `src/lib/` are exempt and may import from `@/api/generated/` directly.

### Types policy

Any interface representing a backend payload must be imported from `@/api/generated/types.gen.ts`. If a type is missing or a generated function returns `unknown`, that is a backend bug — fix the FastAPI response model and regenerate. Do not hand-roll the type.

This extends to runtime values derived from generated types: do not redeclare union literals as standalone arrays or constants. Import the generated type and derive from it (e.g. type the array as `readonly TitleEnum[]` rather than restating `["Mr.", "Ms.", "Mrs."]` without a type anchor).

### Other

- Zustand (`src/auth/store.ts`) for client state only — not for server data
- `<SchoolSelect>` must be scoped to the current project for all building-level forms — do not reuse a global school picker
- `created_by_id == 1` marks system-created rows — render with a subtle "system" badge; hide manual edit/resolve controls on these
- Import alias is `@/` only. Do not use `#/` — it is the Node subpath alias, not the Vite/TS alias. Rewrite any shadcn-CLI-generated `#/` imports to `@/`.
