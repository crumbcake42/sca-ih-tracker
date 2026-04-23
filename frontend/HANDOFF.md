# Session Handoff — Frontend

## Backend changes pending frontend pickup

**Regenerate the OpenAPI client** — the contractors module gained `GET /contractors/`, `GET /contractors/{id}`, `POST /contractors/`, and `PATCH /contractors/` endpoints (Phase 1.5 session 1). These did not exist before. Run the codegen command from `frontend/CLAUDE.md` after the backend is running.

**Breaking change: `GET /work-auths/` now returns a paginated list.** Previously, `GET /work-auths/?project_id=X` returned a single `WorkAuth` object and raised 404 when no work auth existed for that project. It now returns a `PaginatedResponse<WorkAuth>` envelope (`{ items, total, skip, limit }`). When the project has no work auth, `total` is 0 and `items` is `[]` — there is no 404. Any frontend code that reads `response.project_id` directly must be updated to `response.items[0]?.project_id` (and guard for the empty case). Regenerate the OpenAPI client after the backend is running.

---

## Current State

**Sessions 0.5 and 1.1–1.7 complete.** Three-tier layout is live, dead code deleted, `src/shared/` flattened, feature api/ wrappers created, pages layer introduced, auth guard upgraded to async token validation, role-router at `/` added. Polymorphic `<NotesPanel>` primitive built. Testing infrastructure wired (`vitest` + jsdom + RTL + jest-dom + user-event). Storybook 10 configured and stories written for all shared components. Line-ending policy and format-on-save toolchain fixed.

## Session 2.1 — UNBLOCKED, planned, split into 2.1a / 2.1b / 2.1c

All three original backend blockers verified resolved in the regenerated client:

- [x] `types.gen.ts` has `EmployeeCreate` (L426), `EmployeeUpdate` (L522), `PaginatedResponseEmployee` (L835 — note: flat name, no underscores)
- [x] SDK has `createEmployeeEmployeesPost`, `updateEmployeeEmployeesEmployeeIdPatch`, `deleteEmployeeEmployeesEmployeeIdDelete`, plus the full role-mutation set
- [x] `ListEntriesEmployeesGetData.query` is `{ skip?, limit?, search? }`; response is `PaginatedResponseEmployee`

See `ROADMAP.md` Session 2.1 for the split into three sub-sessions: **2.1a** (list + broken-combobox fix + full api/ barrel), **2.1b** (create/edit dialog + detail page with Details tab), **2.1c** (Roles tab with 409/422 error UX).

**⚠️ 2.1a must land first** — `src/fields/EmployeeCombobox.tsx` currently reads `listEmployees` as `Employee[]`, but the regenerated response is `{items, total, skip, limit}`. The combobox will crash the moment the new client is pulled in. 2.1a fixes it in the same session that adds the list page.

**Collateral pickups from other backend work:**

- **`GET /work-auths/` is now paginated** — previously returned a single `WorkAuth` or 404; now returns `PaginatedResponseWorkAuth` (`{items, total, skip, limit}`). Any FE code reading `response.project_id` directly must migrate to `response.items[0]?.project_id` and guard empty. Not yet audited — check during Phase 3 (Session 3.4 Work Auth tab) or sooner if a consumer is found.
- **New contractors endpoints** (`GET/POST/PATCH /contractors/`) — regenerated client exposes them. Not needed until Session 2.3.

---

## What Was Done This Session (Session 2.1 prep — planning + docs)

**Done:**

- Verified all three Session 2.1 backend blockers resolved in the regenerated client: `EmployeeCreate` (L426), `EmployeeUpdate` (L522), `PaginatedResponseEmployee` (L835), full CRUD + role mutation set in `sdk.gen.ts`, `GET /employees/` query params `{ skip?, limit?, search? }`
- Identified that `src/fields/EmployeeCombobox.tsx` will crash on the new paginated response — flagged as must-fix in 2.1a
- Split Session 2.1 into three focused sub-sessions in `ROADMAP.md` (2.1a: list + combobox fix + api barrel; 2.1b: create/edit form + detail/delete; 2.1c: Roles tab with 409/422 UX)
- Added shared-references preamble to the Session 2.1 block in `ROADMAP.md` (template files, form primitives, resolver, error mapping, hooks, test harness, types policy, naming rules) — enough to start any sub-session cold from a fresh machine
- Noted collateral pickups: `work_auths` paginated migration (audit in Session 3.4) and new contractors endpoints (Session 2.3)

**Next:** Session 2.1a — Employees list + broken-combobox fix + full api/ barrel

**Blockers:** none; client is regenerated, blockers cleared

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
