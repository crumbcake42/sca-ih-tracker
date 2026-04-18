# Session Handoff — Frontend

## Current State

**Phase 0 complete. Sessions 1.1 through 1.4 complete.** Schools admin (list, import dialog, detail), admin route guard, and `useFormDialog` are live. TypeScript is clean. **Fix the auth guard before continuing to Session 1.5 — see Blockers.**

## What Was Done This Session (1.4)

### Created

- `src/features/schools/SchoolsListPage.tsx` — list with search + real skip/limit pagination + "Import CSV" button. Columns: code, name, borough, address. `onRowClick` navigates to detail. Uses `PaginatedResponseSchool` — `data.items` for rows, `data.total / data.limit` for `pageCount`.
- `src/features/schools/SchoolImportDialog.tsx` — file input, calls `POST /schools/batch/import`, invalidates list query, shows created count in toast. Resets form on close.
- `src/features/schools/SchoolDetailPage.tsx` — read-only detail card with all school fields. Back link to list. Loader pre-fetches via `queryClient.ensureQueryData`.
- `src/shared/hooks/useFormDialog.ts` — `useFormDialog(onClose?)` returns `{ open, setOpen, onOpenChange }`. Calls `onClose` when dialog closes.
- `src/routes/_authenticated/admin.tsx` — layout route at `/admin`; `beforeLoad` redirects non-admins to `/projects` via `user.is_admin` check.
- `src/routes/_authenticated/admin/schools/index.tsx` — mounts `SchoolsListPage`; declares `validateSearch` with optional `search`, `page`, `pageSize`.
- `src/routes/_authenticated/admin/schools/$schoolId.tsx` — mounts `SchoolDetailPage`; loader pre-fetches school by id.

### Updated

- `src/routeTree.gen.ts` — added admin, admin/schools, and admin/schools/$schoolId routes.
- `src/shared/components/AppShell.tsx` — added admin nav link (visible to `is_admin` users only); fixed import path to `@/auth/hooks`.
- `src/routes/_authenticated.tsx` — fixed import path to `@/components/AppShell`.
- `src/shared/components/DataTable.tsx` — widened `error` prop to `unknown`; render falls back to generic message for non-Error values.
- `src/shared/fields/SchoolCombobox.tsx` — fixed to use `data?.items` (API returns `PaginatedResponseSchool`, not an array).
- `src/shared/hooks/useUrlPagination.ts` / `useUrlSearch.ts` — cast search updater return to `never` to satisfy cross-route type intersection in generic `navigate` calls.
- `src/routes/_authenticated/projects/index.tsx` and `admin/schools/index.tsx` — `validateSearch` return type explicitly typed as `{ search?: string; page?: number; pageSize?: number }` so redirects to these routes don't require search params.

## Architecture Notes

### Import alias convention

Use `@/` for all absolute imports. The `#/` prefix is wrong — do not use it even if shadcn CLI generates it. Always rewrite to `@/`.

### Folder organization

| Kind                         | Location                                        |
| ---------------------------- | ----------------------------------------------- |
| shadcn primitives + `cn()`   | `src/lib/utils.ts`, `src/shared/components/ui/` |
| Pure JS utilities (no React) | `src/lib/[domain].ts` (e.g. `form-errors.ts`)   |
| React hooks                  | `src/shared/hooks/`                             |
| Field/combobox components    | `src/shared/fields/`                            |
| Layout + data components     | `src/shared/components/`                        |

Do **not** create `src/shared/utils/` — pure utilities belong in `src/lib/`.

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

**Fix auth guard, then Session 1.5 — Notes panel.**

### Blockers

**Auth guard does not verify token validity.** `src/routes/_authenticated.tsx` only checks `useAuthStore.getState().token !== null`. A persisted-but-expired token passes the check and the user lands on `/projects` instead of `/login`.

Fix: make `beforeLoad` async, call `GET /users/me` (use `getMeUsersMeGetOptions` from the generated client), and if it fails (any error / 401) call `clearAuth()` and throw `redirect({ to: '/login' })`. On success, the returned user can be stored via `setAuth` if needed, but the token is already in the store — just use the response to verify liveness.

The `_authenticated.tsx` guard is the single chokepoint for all protected routes, so fixing it here covers every page automatically.
