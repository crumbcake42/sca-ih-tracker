# Session Handoff — Frontend

## Current State

**Phase 0 complete. Sessions 1.1 through 1.3 complete.** DataTable primitive and URL-synced hooks are live. Next session is **1.4 — EntityListPage + EntityFormPage**.

## What Was Done This Session (1.3)

### Created

- `src/shared/components/DataTable.tsx` — generic `<DataTable<TData>>` built on TanStack Table v8 + shadcn `<Table>`. Props: `columns`, `data`, `pagination`, `onPaginationChange`, `pageCount`, `isLoading?`, `error?`, `onRowClick?`, `emptyMessage?`, `skeletonRows?`. Uses `manualPagination: true` — all paging is server-side. Pagination controls (prev/next + "Page X of Y") render only when there are rows (hidden during loading/error/empty states).
- `src/shared/hooks/useUrlPagination.ts` — `useUrlPagination(defaultPageSize?)` syncs `PaginationState` with `page` / `pageSize` URL search params via TanStack Router. Converts between 1-indexed URL params and 0-indexed table state. Uses `useSearch({ strict: false })` cast to `Record<string, unknown>` so it works from any route without requiring a route-specific schema.
- `src/shared/hooks/useUrlSearch.ts` — `useUrlSearch(param?)` returns `[value, setValue]` for a single string filter param. Resetting the value also clears `page` so results always restart from page 1.

### Updated

- `src/routes/_authenticated/projects/index.tsx` — migrated from local `useState` to `useUrlSearch` + `useUrlPagination`. Replaced hand-rolled table/loading/empty JSX with `<DataTable>` + `ColumnDef<Project>[]`. Added `validateSearch` to the route so TanStack Router knows the expected params. `pageCount={1}` hardcoded — the projects endpoint returns `Array<Project>` with no total count, so real multi-page support must wait for the backend to wrap the response.

### Deferred

- `useFormDialog()` — still deferred; build when first needed by a concrete form in Session 1.4.
- `onRowClick` navigation on projects list — detail route doesn't exist yet; wired when the project detail route is built.

## Architecture Notes

### Import alias convention

Use `@/` for all absolute imports. The `#/` prefix was an early mistake and has been removed from new code. `src/lib/utils.ts` remains at that path (shadcn-managed); `components.json` references it as `@/lib/utils`.

### Folder organization

| Kind | Location |
|---|---|
| shadcn primitives + `cn()` | `src/lib/utils.ts`, `src/shared/components/ui/` |
| Pure JS utilities (no React) | `src/lib/[domain].ts` (e.g. `form-errors.ts`) |
| React hooks | `src/shared/hooks/` |
| Field/combobox components | `src/shared/fields/` |
| Layout + data components | `src/shared/components/` |

Do **not** create `src/shared/utils/` — pure utilities belong in `src/lib/`.

### Combobox pattern

Both comboboxes use `shouldFilter={false}` on `<Command>` so filtering is handled explicitly (server-side for School, client-side for Employee). Trigger button width is matched to the popover via `w-[var(--radix-popover-trigger-width)]`. Selecting the already-selected value deselects (toggles to `null`).

### DataTable pattern

`useReactTable` is called with `manualPagination: true` and `pageCount` from the API response (total ÷ page size). The route is responsible for declaring `validateSearch` with `page` / `pageSize` / filter params; `useUrlPagination` and `useUrlSearch` read them via `useSearch({ strict: false })` so they work generically across routes.

Routes that use pagination must call `useUrlPagination` and pass `{ pagination, onPaginationChange }` to `<DataTable>`. Column definitions are declared as a module-level constant (`const columns: ColumnDef<T>[] = [...]`) outside the component to avoid re-creating the array on each render.

## Next Step

**Session 1.4 — EntityListPage + EntityFormPage.**

Key tasks:

1. `EntityConfig<T>` type — drives columns, form fields, API hooks, labels.
2. `<EntityListPage>` — wraps `<DataTable>` with a title bar, create button, and URL-synced search.
3. `<EntityFormPage mode="create"|"edit">` — wraps react-hook-form + `Field`/`FieldGroup` with standardized submit/cancel.
4. `<EntityFormDialog>` — inline create variant (popover/dialog, no navigation).
5. `useFormDialog()` hook — open/close state + reset on close.
6. Create `src/PATTERNS.md` at end of this session once the shapes are stable.

**Blockers:** none
