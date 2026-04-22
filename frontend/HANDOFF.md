# Session Handoff — Frontend

## Current State

**Sessions 0.5 and 1.1–1.6 complete.** Three-tier layout is live, dead code deleted, `src/shared/` flattened, feature api/ wrappers created, pages layer introduced, auth guard upgraded to async token validation, role-router at `/` added. Polymorphic `<NotesPanel>` primitive built. Testing infrastructure wired (`vitest` + jsdom + RTL + jest-dom + user-event). Storybook 10 configured and stories written for all shared components.

## What Was Done This Session (Session 1.6 — Storybook)

**Done:**

- Installed Storybook 10 (`storybook`, `@storybook/react-vite`, `@storybook/addon-a11y`, `@storybook/addon-docs`, `@storybook/addon-vitest`, `@chromatic-com/storybook`, `@vitest/browser`, `@vitest/coverage-v8`, `playwright`)
- `.storybook/main.ts` — framework `@storybook/react-vite`; addons; `viteFinal` strips all `"tanstack"` plugins to avoid SSR transform errors (same fix as vitest's dedicated config)
- `.storybook/preview.tsx` — imports `../src/styles.css` (Tailwind tokens); global `withQueryClient` decorator wraps every story in a fresh `QueryClient` (retries off, gcTime 0)
- `src/test/queryClient.ts` — extracted `createTestQueryClient()` shared by both `renderWithProviders` and the Storybook preview decorator
- `src/features/employees/api/employees.ts` — created just-in-time api wrapper exporting `listEmployeesOptions` / `listEmployeesQueryKey`
- Wrote five story files:
  - `src/components/DataTable.stories.tsx` — Default, Loading, Empty, Error variants
  - `src/components/AppShell.stories.tsx` — Default (admin user seeded in Zustand), Unauthenticated; memory-router decorator for `<Link>` components
  - `src/fields/SchoolCombobox.stories.tsx` — Default, WithSelection; cache pre-seeded via `listSchoolsQueryKey`
  - `src/fields/EmployeeCombobox.stories.tsx` — Default, WithSelection; cache pre-seeded via `listEmployeesQueryKey`
  - `src/features/notes/components/NotesPanel.stories.tsx` — Populated (manual + system + resolved notes), Empty
- Vitest workspace split into two named projects: `unit` (jsdom, `pnpm test`) and `storybook` (Playwright, `pnpm test:stories`); `pnpm test` targets only `unit` so it never needs Playwright
- Deleted wizard-generated `src/stories/` boilerplate
- `src/PATTERNS.md` — added Storybook section
- `pnpm test` → 2/2 green; `tsc --noEmit` clean

**Next:** Session 2.1 — Employees admin CRUD (second concrete entity; validates generics shape)

**Blockers:** `pnpm test:stories` (Storybook/Playwright integration) requires `pnpm exec playwright install chromium` before first use. Not a blocker for regular development.

## What Was Done Previously (Session 0.5 — Test Infrastructure)

**Done:**

- Installed `@testing-library/user-event` and `@testing-library/jest-dom`
- Created `vitest.config.ts` — dedicated config (jsdom, globals, `src/test/setup.ts`) that does NOT load the TanStack Start plugin (SSR transforms break vitest)
- Updated `tsconfig.json` — added `"vitest/globals"` and `"@testing-library/jest-dom"` to `types` for zero-import globals and matchers
- Created `src/test/setup.ts` — imports jest-dom/vitest extension, registers `afterEach(cleanup)`
- Created `src/test/renderWithProviders.tsx` — `QueryClient` wrapper for component tests (retries off, gcTime 0); router wrapping deferred until first router-aware test
- Created `src/test/smoke.test.tsx` — 2 tests: RTL + jest-dom render assertion, `@/` alias resolution via `cn()`
- `pnpm test` → 2/2 green; `tsc --noEmit` and `pnpm check` clean
- Added **Testing** section to `src/PATTERNS.md`

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
