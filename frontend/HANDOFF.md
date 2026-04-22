# Session Handoff — Frontend

## Current State

**Phase 0 complete. Sessions 1.1 through 1.4 complete. Structural refactor complete.** Three-tier layout is live, dead code deleted, `src/shared/` flattened, feature api/ wrappers created, pages layer introduced, auth guard upgraded to async token validation, role-router at `/` added.

## What Was Done This Session (structural refactor)

**Done:**

- Deleted dead code: `src/auth/{provider,context,types}.tsx`, `src/shared/components/{Header,Footer,ThemeToggle}.tsx`, `src/routes/{index,about}.tsx`, stray `console.log` in `_authenticated.tsx`
- Flattened `src/shared/` → `src/{components,hooks,fields}/`; `src/lib/` unchanged
- Removed `@/components/*` and `@/hooks/*` tsconfig aliases (only `@/*` remains); removed `#/*` from `package.json`
- Created feature api/ wrappers: `features/schools/api/schools.ts`, `features/projects/api/projects.ts`, `features/auth/api/hooks.ts`; cross-cutting `src/auth/api.ts` for auth guard
- Introduced `src/pages/` layer: login, dashboard (placeholder), projects list, admin overview, admin/schools list + detail
- Split existing school + project route-body files into prop-driven feature components + URL-wired page files
- Rewrote `_authenticated.tsx` guard: now async, calls `/users/me` via `queryClient.ensureQueryData`, clears auth and redirects on failure
- Added `_authenticated/index.tsx` role-router (`admin`/`superadmin` → `/admin`, else → `/dashboard`)
- Added `_authenticated/dashboard.tsx` and `_authenticated/admin/index.tsx` placeholder routes
- Updated admin guard to include `superadmin` alongside `admin`
- Added eslint `no-restricted-imports` rules enforcing layer boundaries
- Created `src/PATTERNS.md`
- `pnpm check` and `tsc --noEmit` clean

**Next:** Session 1.5 — Notes panel (`<NotesPanel entityType entityId>`)

**Blockers:** none

## Architecture Notes

### Import alias convention

Use `@/` for all absolute imports. The `#/` prefix is wrong — do not use it even if shadcn CLI generates it. Always rewrite to `@/`.

### Folder organization

| Kind                                       | Location                                      |
| ------------------------------------------ | --------------------------------------------- |
| shadcn primitives + `cn()`                 | `src/lib/utils.ts`, `src/components/ui/`      |
| Pure JS utilities (no React)               | `src/lib/[domain].ts` (e.g. `form-errors.ts`) |
| React hooks (shared)                       | `src/hooks/`                                  |
| Field/combobox components (shared)         | `src/fields/`                                 |
| Layout + data components (shared)          | `src/components/`                             |
| Domain building blocks                     | `src/features/<domain>/components/`           |
| Domain API wrappers (TanStack Query layer) | `src/features/<domain>/api/`                  |
| URL-bound page compositions                | `src/pages/<route>/`                          |
| Route config only                          | `src/routes/`                                 |

Do **not** create `src/utils/` — pure utilities belong in `src/lib/`.

Import boundary rule: `routes/ → pages/ → features/ → components/, hooks/, fields/, lib/`. Features never import from `pages/` or `routes/`. Pages use `getRouteApi('/path')` and never import `Route` from a route file. Enforced via eslint `no-restricted-imports`. See `src/PATTERNS.md` for full detail.

### validateSearch typing

`validateSearch` return type must be explicitly annotated with `?` optional keys (e.g. `): { search?: string; page?: number; pageSize?: number } =>`). Without this, TanStack Router treats every returned key as required and demands them in redirect calls.

### Paginated response shape

Schools (and all paginated endpoints) return `PaginatedResponse<T>` — use `data.items` for the row array, `data.total / data.limit` for pageCount. Do not default `data` to `[]` — default to `data?.items ?? []`.

### Combobox pattern

Both comboboxes use `shouldFilter={false}` on `<Command>` so filtering is handled explicitly (server-side for School, client-side for Employee). Trigger button width is matched to the popover via `w-[var(--radix-popover-trigger-width)]`. Selecting the already-selected value deselects (toggles to `null`).

### DataTable pattern

`useReactTable` is called with `manualPagination: true` and `pageCount` from the API response (total ÷ page size). The route is responsible for declaring `validateSearch` with `page` / `pageSize` / filter params; `useUrlPagination` and `useUrlSearch` read them via `useSearch({ strict: false })` so they work generically across routes.

Routes that use pagination must call `useUrlPagination` and pass `{ pagination, onPaginationChange }` to `<DataTable>`. Column definitions are declared as a module-level constant (`const columns: ColumnDef<T>[] = [...]`) outside the component to avoid re-creating the array on each render.

## Next Step

**Session 1.5 — Notes panel.**

Build `<NotesPanel entityType entityId>` in `src/features/notes/components/NotesPanel.tsx`. Key constraints from ROADMAP.md:
- System notes (`note_type != null`) get distinct visual treatment and no Resolve button
- Replies are one level deep; collapse/expand
- One component serves all four entity types (`project` | `time_entry` | `deliverable` | `sample_batch`)
- Wrap `listNotesNotesEntityTypeEntityIdGetOptions` etc. under `src/features/notes/api/notes.ts` before using in the component
