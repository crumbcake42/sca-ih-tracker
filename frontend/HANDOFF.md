# Session Handoff — Frontend

## Current State

**Phase 0 complete. Sessions 1.1 through 1.4 complete.** Schools admin (list, import dialog, detail), admin route guard, and `useFormDialog` are live. TypeScript is clean.

> **PRIORITY: Execute the structural refactor before starting Session 1.5.** The plan is at `.claude/plans/i-want-to-update-wise-unicorn.md`. Session 1.5 (Notes panel) starts only after the refactor is done and TypeScript + lint are clean.

## What Was Done This Session (architecture planning)

No code was written. This session finalized the frontend architecture and updated all documentation to reflect it.

### Decisions made

- **Three-tier layout** — `routes/ → pages/ → features/ → components/hooks/fields/lib/`. Features are routing-agnostic (prop-driven). Pages own URL↔state wiring via `getRouteApi`. Route files are config-only and import only from `@/pages/`. Enforced via eslint `no-restricted-imports`.
- **`src/shared/` flattened** — contents move to `src/{components,hooks,fields}/`. `src/lib/` stays (shadcn references it by name).
- **`src/pages/` introduced** — one subdirectory per route; even single-feature routes get a page file so features stay routing-agnostic.
- **API wrapper layer** — feature `api/` files re-export `*Options`/`*Mutation`/`*QueryKey` helpers under domain-owned names (TanStack Query layer only, just-in-time). No raw `sdk.gen` re-exports.
- **Types policy** — all backend interfaces from `@/api/generated/types.gen.ts`; missing type = backend bug, not a frontend workaround.
- **Auth guard** — must be async and validate token against `/users/me`, not just check for presence.
- **Root `/` role-routes** — `admin|superadmin` → `/admin`; everyone else → `/dashboard` (placeholder page until Phase 5).
- **Dead code identified** — `src/auth/{provider,context,types}.tsx`, `src/shared/components/{Header,Footer,ThemeToggle}.tsx`, `src/routes/{index,about}.tsx`.

### Documents updated

- `ROADMAP.md` — architecture principle §5 rewritten (three-tier layering + §5a–§5d sub-policies); repo layout diagram replaced; Phase 0.3 updated; PATTERNS.md note updated.
- `HANDOFF.md` — this file; restructure priority added; folder table updated; Next Step rewritten as 11-step refactor checklist.
- `CLAUDE.md` — fixed `#/` → `@/` bug; Architecture Notes rewritten with named subsections for three-tier structure, wrapper policy, and types policy.
- Plan file — `.claude/plans/i-want-to-update-wise-unicorn.md` — full implementation plan with migration table, verification steps, and critical files list.

## Architecture Notes

### Import alias convention

Use `@/` for all absolute imports. The `#/` prefix is wrong — do not use it even if shadcn CLI generates it. Always rewrite to `@/`.

### Folder organization (post-refactor target)

The refactor moves `src/shared/` into the root and introduces `src/pages/` and feature-level `api/` wrappers. See ROADMAP.md §5 and the plan file for the full migration table. After the refactor:

| Kind | Location |
|---|---|
| shadcn primitives + `cn()` | `src/lib/utils.ts`, `src/components/ui/` |
| Pure JS utilities (no React) | `src/lib/[domain].ts` (e.g. `form-errors.ts`) |
| React hooks (shared) | `src/hooks/` |
| Field/combobox components (shared) | `src/fields/` |
| Layout + data components (shared) | `src/components/` |
| Domain building blocks | `src/features/<domain>/components/` |
| Domain API wrappers (TanStack Query layer) | `src/features/<domain>/api/` |
| URL-bound page compositions | `src/pages/<route>/` |
| Route config only | `src/routes/` |

Do **not** create `src/utils/` — pure utilities belong in `src/lib/`.

Import boundary rule: `routes/ → pages/ → features/ → components/, hooks/, fields/, lib/`. Features never import from `pages/` or `routes/`. Pages use `getRouteApi('/path')` and never import `Route` from a route file.

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

**Execute the structural refactor (plan at `.claude/plans/i-want-to-update-wise-unicorn.md`), then Session 1.5 — Notes panel.**

### Refactor scope

1. Delete dead code: `src/auth/{provider,context,types}.tsx`, `src/shared/components/{Header,Footer,ThemeToggle}.tsx`, `src/routes/{index,about}.tsx`, stray `console.log` in `_authenticated.tsx`.
2. Move `src/shared/{components,hooks,fields}` → `src/{components,hooks,fields}`. Update all import paths.
3. Remove redundant tsconfig aliases (`@/components/*`, `@/hooks/*`); remove `"imports": { "#/*": ... }` from `package.json`.
4. Create `src/pages/` with extracted page components (login, dashboard placeholder, projects list, admin/schools list+detail, admin overview).
5. Create `src/features/auth/`, `src/features/projects/api/`, `src/features/schools/api/` with just-in-time wrappers. Move `src/auth/hooks.ts` → `src/features/auth/api/hooks.ts`.
6. Refactor existing school/project components to be routing-agnostic (prop-driven, no `Route.useSearch` calls).
7. Fix `_authenticated.tsx` guard: make `beforeLoad` async, call `/users/me` via `getMeUsersMeGetOptions`, on failure `clearAuth()` + `throw redirect({ to: '/login' })`.
8. Add `_authenticated/index.tsx` role-router and `_authenticated/dashboard.tsx` placeholder.
9. Create `src/PATTERNS.md` codifying the three-tier layering, wrapper policy, types policy, routing policy.
10. Add eslint `no-restricted-imports` rules enforcing layer boundaries.
11. Run `pnpm check` + `tsc --noEmit` + smoke-test the auth flows manually.

### Blockers

**Auth guard does not verify token validity.** `src/routes/_authenticated.tsx` only checks `useAuthStore.getState().token !== null`. Fixed in step 7 above.
