# Session Handoff — Frontend

## Backend changes pending frontend pickup

**Regenerate the OpenAPI client** — the contractors module gained `GET /contractors/`, `GET /contractors/{id}`, `POST /contractors/`, and `PATCH /contractors/` endpoints (Phase 1.5 session 1). These did not exist before. Run the codegen command from `frontend/CLAUDE.md` after the backend is running.

**Breaking change: `GET /work-auths/` now returns a paginated list.** Previously, `GET /work-auths/?project_id=X` returned a single `WorkAuth` object and raised 404 when no work auth existed for that project. It now returns a `PaginatedResponse<WorkAuth>` envelope (`{ items, total, skip, limit }`). When the project has no work auth, `total` is 0 and `items` is `[]` — there is no 404. Any frontend code that reads `response.project_id` directly must be updated to `response.items[0]?.project_id` (and guard for the empty case). Regenerate the OpenAPI client after the backend is running.

---

## Current State

**Sessions 0.5, 1.1–1.7, 2.1a, 2.1b, 2.1c, and 1.5A complete.** Employees feature is fully implemented. Phase 1.5A theme work is done: island/sea palette removed, shadcn tokens are the sole palette, dark/light/auto toggle live in AppShell.

**Next is Phase 1.5B — Admin shell (WordPress-style sidebar layout).**

**Collateral pickups from other backend work:**

- **`GET /work-auths/` is now paginated** — previously returned a single `WorkAuth` or 404; now returns `PaginatedResponseWorkAuth` (`{items, total, skip, limit}`). Any FE code reading `response.project_id` directly must migrate to `response.items[0]?.project_id` and guard empty. Not yet audited — check during Phase 3 (Session 3.4 Work Auth tab) or sooner if a consumer is found.
- **New contractors endpoints** (`GET/POST/PATCH /contractors/`) — regenerated client exposes them. Not needed until Session 2.3.

**Priority after completing phase 2.1** - issues and patterns to resolve (written by me, the user, not Claude)

- commit to file structure decision: explain why entity fields like employee and school combobox are in src/fields instead of src/[entity]/components/
- discuss testing strategy. is it not in roadmap or is there a reason why the code we've written so far doesn't need unit/regression/integration tests?

---

## What Was Done This Session (Session 1.5A — Theme consolidation + dark/light toggle)

**Done:**

- Deleted island/sea palette from `src/styles.css` entirely — all `--sea-*`, `--lagoon*`, `--palm`, `--sand`, `--foam`, `--surface*`, `--line`, `--inset-glint`, `--kicker`, `--bg-base`, `--header-bg`, `--chip-*`, `--link-bg-hover`, `--hero-*` vars and their dark-mode overrides; shadcn neutral tokens are now the sole palette
- Removed global `a { color: var(--lagoon-deep) }` rule — fixes Button-as-Link legibility everywhere
- Removed island-specific CSS classes (`.island-shell`, `.feature-card`, `.island-kicker`, `.nav-link`, `.site-footer`, `.display-title`) and `body::before`/`body::after` decorative pseudo-elements
- Switched `html { @apply font-mono }` → `html { @apply font-sans }` in `@layer base`; updated Google Fonts import to Manrope-only (removed Fraunces)
- Updated `code` styles to use `var(--border)` + `var(--muted)` (shadcn tokens) instead of removed island vars
- Removed `--font-heading` from `@theme inline` (was pointing at `--font-mono`; heading style no longer needed)
- Simplified `THEME_INIT_SCRIPT` in `src/routes/__root.tsx` — drops `data-theme` attribute; now only toggles `.dark` class + `colorScheme`
- Created `src/lib/theme.ts` — `getResolvedTheme()`, `setTheme(value: Theme)`, `useTheme()` via `useSyncExternalStore`; no Zustand slice; listeners set for cross-component sync
- Created `src/components/ThemeToggle.tsx` — three-state cycle button (auto → light → dark → auto) using Phosphor `MonitorIcon` / `SunIcon` / `MoonIcon`; `aria-label` + `title` with current state
- Updated `src/components/AppShell.tsx` — added `<ThemeToggle />` between user chip and sign-out button
- Updated `.storybook/preview.tsx` — added `withTheme` decorator applying `.dark` class from `globals.theme`; added `globalTypes.theme` toolbar (light/dark); decorators order: `[withTheme, withQueryClient]`
- `pnpm tsc --noEmit`, `pnpm test` (5/5 green), `pnpm check` — all clean

**Next:** Session 1.5B — Admin shell (WordPress-style sidebar layout)

**Blockers:** none

---

## What Was Done Previously (Session 2.1c — Roles tab)

**Done:**

- Created `src/features/employees/components/EmployeeRoleFormDialog.tsx` — single dialog for create and edit; `role?: EmployeeRole` prop; Zod schema with required `role_type`/`start_date`/`hourly_rate`, optional `end_date`; in edit mode `role_type` + `start_date` are disabled per `EmployeeRoleUpdate` immutability; 409 (date-range overlap) → `setError("root.serverError")` → inline `role="alert"` banner, no toast; 422 (`end_date <= start_date`) → `applyServerErrors` lands on `end_date`; `handleError` checks 409 first then 422; `ROLE_TYPE_OPTIONS` typed as `readonly EmployeeRoleType[]` (anchored, not hand-rolled)
- Created `src/features/employees/components/EmployeeRolesTab.tsx` — fetches `listEmployeeRolesOptions`; shadcn `Table` (no pagination — endpoint returns `Array<EmployeeRole>`); "Add role" button; inline Edit/Delete buttons per row; `DeleteRoleDialog` internal component (simple confirm, error via toast); all mutations invalidate `listEmployeeRolesQueryKey`
- Updated `src/features/employees/components/EmployeeDetail.tsx` — replaced disabled "Roles" tab stub with live `<EmployeeRolesTab employeeId={employeeId} />`
- Created `src/features/employees/components/EmployeeRoleFormDialog.test.tsx` — 3 tests: 409 renders inline banner + asserts no toast; 422 attaches to `end_date` field; `role_type` + `start_date` disabled in edit mode
- `pnpm tsc --noEmit`, `pnpm test` (5/5 green), `pnpm check` — all clean

**Next:** Session 2.2 — Extract generics + retrofit (Schools + Employees → `EntityListPage`/`EntityFormDialog`)

**Blockers:** none

---

## What Was Done Previously (Session 2.1b — EmployeeFormDialog + EmployeeDetail + delete 409)

**Done:**

- Created `src/features/employees/components/EmployeeFormDialog.tsx` — single dialog for create and edit; `employee?: Employee` prop; Zod schema with required `first_name`/`last_name`, optional rest; `TitleEnum`-typed options array (not a hand-rolled literal — follows Types policy); `applyServerErrors` on 422, fall back to toast; invalidates list + detail on success
- Created `src/features/employees/components/EmployeeDetail.tsx` — `getEmployeeOptions` query; shadcn `Tabs` with Details tab (DetailRow list + Edit/Delete buttons) and disabled Roles tab (placeholder content for 2.1c); `DeleteConfirmDialog` keeps dialog open and renders backend `detail` string inline on 409; navigates to `/admin/employees` on successful delete
- Created `src/pages/admin/employees/detail.tsx` — `getRouteApi` page wrapper
- Created `src/pages/admin/employees/loader.ts` — `prefetchEmployee` via `queryClient.ensureQueryData`
- Updated `src/routes/_authenticated/admin/employees/$employeeId.tsx` — replaced placeholder with loader + `EmployeeDetailPage`
- Updated `src/pages/admin/employees/index.tsx` — wired "Add employee" button to open `EmployeeFormDialog` in create mode
- Extended `frontend/CLAUDE.md` Types policy: do not redeclare values derivable from a generated type (covers runtime arrays seeded from union literals)
- `pnpm tsc --noEmit`, `pnpm test` (2/2 green), `pnpm check` — all clean

**Next:** Session 2.1c — Roles tab (`EmployeeRolesTab` + `EmployeeRoleFormDialog` with 409 inline banner + 422 on `end_date`)

**Blockers:** none

---

## What Was Done Previously (Session 2.1a — Employees list + combobox fix + api barrel)

**Done:**

- Expanded `src/features/employees/api/employees.ts` to full barrel: `listEmployeesOptions/QueryKey`, `getEmployeeOptions/QueryKey`, `createEmployeeMutation`, `updateEmployeeMutation`, `deleteEmployeeMutation`, `getEmployeeConnectionsOptions/QueryKey`, `listEmployeeRolesOptions/QueryKey`, `createEmployeeRoleMutation`, `updateEmployeeRoleMutation`, `deleteEmployeeRoleMutation`
- Fixed `src/fields/EmployeeCombobox.tsx`: switched import to feature barrel, reads `data?.items ?? []` (was crashing on `PaginatedResponseEmployee`), server-side search debounced 250ms via `useDebounce`
- Updated `src/fields/EmployeeCombobox.stories.tsx`: cache seed updated to `{items, total, skip, limit}` paginated envelope
- Created `src/features/employees/components/EmployeesList.tsx` — prop-driven; module-scope columns (Name, Title, Email, ADP ID); `pageCount = Math.ceil(total/limit)`
- Created `src/pages/admin/employees/index.tsx`, `src/routes/_authenticated/admin/employees/index.tsx` (with `validateSearch`), and `$employeeId.tsx` placeholder
- Ran `pnpm exec tsr generate` to pick up new routes; fixed `eslint-plugin-prettier` missing package

---

## What Was Done Previously (Session 1.7 — Storybook cleanup + tooling)

**Done:**

- Diagnosed ~90 phantom "modified" files in `git status` as CRLF/LF noise — only 10 files had real content diffs; rest were working-copy CRLF vs LF-stored blobs with no `.gitattributes` enforcing a policy
- Created `.gitattributes` at repo root (`* text=auto eol=lf`) — single source of truth; `core.autocrlf=input` means no OS-level conversion fights
- Fixed `prettier.config.js`: changed `endOfLine: "crlf"` → `"auto"` (was the root cause of phantom diffs); also restored double-quotes + semicolons which had been accidentally stripped by prettier running on itself
- Installed `eslint-plugin-prettier` + `eslint-config-prettier` (peer dep); updated `eslint.config.js` to spread `eslintPluginPrettier.configs["flat/recommended"]` — prettier rules now enforced via ESLint
- Updated root `.vscode/settings.json`: ESLint as default formatter for `[typescript]` + `[typescriptreact]`, `eslint.format.enable: true`, `eslint.validate` list, `files.eol: "auto"`; removed stale `prettier.endOfLine: "lf"`
- Updated `frontend/.vscode/settings.json`: same ESLint formatter settings (kept frontend-specific `routeTree.gen.ts` exclusions); removed `prettier.requireConfig`
- Fixed `tsconfig.json`: added `.storybook/**/*.ts` and `.storybook/**/*.tsx` to `include` — `**` glob in TypeScript does not match dotfile directories so `.storybook/` was excluded, causing ESLint parse errors on `main.ts` and `preview.tsx`
- Ran `git add --renormalize .`: cleared the 80 CRLF-noise entries; left only 10 real diffs staged
- `pnpm tsc --noEmit`, `pnpm test` (2/2 green), `pnpm check` — all pass; format-on-save working via ESLint extension

**Pending before next session:**

- Visual Storybook smoke test (`pnpm storybook`) — confirm each story renders; commit `7e08157` still says "not tested yet"
- Two commits (Commit A: `.gitattributes` + prettier config + vscode settings; Commit B: storybook style + renormalized files)

**Next:** Session 2.1 — Employees admin CRUD (second concrete entity; validates generics shape)

**Blockers:** `pnpm test:stories` (Storybook/Playwright integration) requires `pnpm exec playwright install chromium` before first use. Not a blocker for regular development.

## What Was Done Previously (Session 1.6 — Storybook)

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
