# Session Handoff — Frontend

## Current State

**Phase 0 complete. Sessions 1.1 and 1.2 complete.** Form primitives and field comboboxes are live. Next session is **1.3 — DataTable primitive**.

## What Was Done This Session (1.2)

### Created

- `src/lib/form-errors.ts` — `applyServerErrors<T>` maps FastAPI 422 `detail[{loc, msg}]` onto react-hook-form `setError`. Returns `true` if it handled a recognized 422 (so callers can fall back to a toast on `false`).
- `src/shared/hooks/useDebounce.ts` — generic `useDebounce<T>(value, delayMs)` hook.
- `src/shared/fields/SchoolCombobox.tsx` — Popover + Command combobox. Server-side search via `listEntriesSchoolsGetOptions({ query: { search } })`, debounced 250ms. Props: `value: number | null`, `onChange: (id: number | null) => void`.
- `src/shared/fields/EmployeeCombobox.tsx` — same pattern, but full list fetched once and filtered client-side (no server search param on that endpoint). Props: same as above.

### Config changes

- `tsconfig.json` — removed `#/*` alias; now uses `@/*` only. Added `@/components/*` → `src/shared/components/*` and `@/hooks/*` → `src/shared/hooks/*`.
- `components.json` — updated all aliases from `#/` to `@/`. `"hooks"` resolves to `src/shared/hooks/` via the new tsconfig alias.
- `package.json` — `imports` field now correctly uses `#/*` (required by Node.js subpath imports spec).

### Deferred from 1.2 scope

- `useFormDialog()` — deferred to Session 1.3 or when first needed by a concrete form.

## Architecture Notes

### Import alias convention

Use `@/` for all absolute imports. The `#/` prefix was an early mistake and has been removed. `src/lib/utils.ts` remains at that path (shadcn-managed); `components.json` references it as `@/lib/utils`.

### Folder organization

| Kind | Location |
|---|---|
| shadcn primitives + `cn()` | `src/lib/utils.ts`, `src/shared/components/ui/` |
| Pure JS utilities (no React) | `src/lib/[domain].ts` (e.g. `form-errors.ts`) |
| React hooks | `src/shared/hooks/` |
| Field/combobox components | `src/shared/fields/` |
| Layout components | `src/shared/components/` |

Do **not** create `src/shared/utils/` — pure utilities belong in `src/lib/`.

### Combobox pattern

Both comboboxes use `shouldFilter={false}` on `<Command>` so filtering is handled explicitly (server-side for School, client-side for Employee). Trigger button width is matched to the popover via `w-[var(--radix-popover-trigger-width)]`. Selecting the already-selected value deselects (toggles to `null`).

## Next Step

**Session 1.3 — DataTable primitive.**

Key tasks:

1. `<DataTable columns data pagination filters>` built on TanStack Table + shadcn `<Table>`.
2. URL-synced pagination + filters via TanStack Router search params.
3. Empty state, loading skeleton, error state slots.
4. Row click → navigate to detail route.
5. `useFormDialog()` hook — can be built here if DataTable scope is light, otherwise push to 1.4.

**Blockers:** none
