# SCA IH Tracker — Frontend Roadmap

Companion to `backend/data/roadmap.md`. The backend is feature-complete through Phase 6 (closure + record locking); Phase 6.5 (required-docs silos, expected entities, templates) is planned but not yet implemented.

---

## Stack

- **Vite + React + TypeScript** (project already scaffolded elsewhere)
- **TanStack Router** (file-based routing, route-level loaders + `beforeLoad` guards)
- **TanStack Query** (server state, cache invalidation, optimistic updates)
- **shadcn/ui** (`radix-lyra` style) + Tailwind (component primitives)
- **react-hook-form + zod v4** — use `standardSchemaResolver` from `@hookform/resolvers/standard-schema`; no `form` shadcn component in this style — use `Field` / `FieldGroup` / `FieldError` from `@/components/ui/field`
- **`@hey-api/openapi-ts`** with the `@tanstack/react-query` plugin (client + typed query/mutation hooks generated from `/openapi.json`)
- **Zustand** for the tiny amount of true client state (auth user, admin-view toggle) — context would also work but Zustand survives refactors better

---

## Non-obvious items the OpenAPI schema alone will not tell you

These are things a Claude session must know before designing screens — schema shape only tells half the story.

### Auth shape

- `POST /auth/token` uses **OAuth2 password flow** (`OAuth2PasswordRequestForm`). The request body is **form-encoded** (`application/x-www-form-urlencoded`) with `username` and `password` fields — NOT JSON. Generated client code often gets this wrong; verify before using the generated login mutation.
- `GET /users/me` returns the current user with their role and permissions; use its success/failure as the authentication gate.
- Permissions live on `user.role.permissions[]`. Per-action gating should check permission names, not role names. Role-name check (`admin` / `manager`) is fine only for the coarse admin-vs-manager **layout** toggle.
- JWT is a bearer token. Store in memory + refresh on load from `localStorage`; all generated client calls must include an `Authorization: Bearer …` header. Set this once in an axios/fetch interceptor so the generated hooks pick it up.

### Project status is derived, not a column

- `Project` model has `is_locked: bool` and little else on status. The real status comes from `GET /projects/{id}/status` (returns `ProjectStatusRead` — `status`, `has_work_auth`, `pending_rfa_count`, `outstanding_deliverable_count`, `unconfirmed_time_entry_count`, `blocking_issues[]`).
- Any list view that shows project status must either call this per-row (bad — N+1) or surface a dashboard-style aggregate endpoint (Phase 7 on the backend — **does not exist yet**). For now, keep project-status display on the detail page only. Do not build a "status column" in the project list until the dashboard endpoints land.

### Blocking issues and notes are polymorphic

- Notes attach to four entity types: `project` | `time_entry` | `deliverable` | `sample_batch`. One `<NotesPanel entityType="…" entityId={…} />` component serves all four.
- Closure gate is `GET /projects/{id}/blocking-issues` — an aggregator across the whole project tree. This is the endpoint the manager dashboard should hammer.
- Replies are one level deep only. System notes (`note_type != null`) cannot be manually resolved — they auto-resolve when the underlying condition clears. UI must hide the "Resolve" button on system notes.

### Project-level vs building-level split

Three paired sets of endpoints. Each pair corresponds to the same logical concept but at different granularity, and **they must be rendered as two tabs or two sections, not merged**:

| Project-level             | Building-level                  |
| ------------------------- | ------------------------------- |
| `work_auth_project_codes` | `work_auth_building_codes`      |
| `project_deliverables`    | `project_building_deliverables` |
| `rfa_project_codes`       | `rfa_building_codes`            |

Building-level records are keyed by composite `(project_id, school_id)` referring to `project_school_links`. Any building-level form must first pick a school that is actually linked to the project. A `<SchoolSelect>` scoped to the current project is a required primitive — do not reuse a global school picker here.

### Deliverables have two independent status tracks

Every deliverable row carries both `internal_status` (5 values) and `sca_status` (6 values). The first three `sca_status` values (`pending_wa`, `pending_rfa`, `outstanding`) are **derived** by the backend and the UI must render them read-only; the last three (`under_review`, `rejected`, `approved`) are manual. `internal_status.blocked` requires a `notes` body. The UI should present two parallel status pickers with the derived states visually distinct (badge + "auto" hint).

### Config+data meta-model for lab results

Sample types, subtypes, unit types, and turnaround options are **admin-managed rows**, not enums. Adding a new sample type is a `POST /lab-results/config/sample-types` call — no code change, no migration. UI must support CRUD of these as first-class admin entities.

Unit type is scoped to its sample type. A `<SampleUnitTypeSelect sampleTypeId={x}>` component should filter the dropdown — do not present a flat list or users will pick mismatches and get 422.

### Time entry overlap UX

`POST /time-entries/` and `PATCH /time-entries/{id}` return **422 with the conflicting entry's ID** when an overlap would be created. The form must catch the 422, parse out the conflicting `time_entry_id`, and render a link/button ("View the conflicting entry") rather than a generic "could not save" message. This is the single biggest manager-UX pitfall.

### Quick-add

`POST /lab-results/batches/quick-add` creates an `assumed` time entry + sample batch atomically. This is the primary manager entry point for field days where times aren't known yet. Do not force the manager to create the time entry separately — the quick-add path is a key UX simplification.

### System-created records

`created_by_id == 1` (the seeded `SYSTEM_USER_ID`) marks a system-created row. Assumed time entries, system notes, auto-resolution records all look like this. The UI should display these with a subtle badge ("system" / "auto") so managers know what they can and cannot edit.

### Closure returns 409 with blocking issues

`POST /projects/{id}/close` returns `409` with the full `blocking_issues[]` payload when gates fail. Do not show a generic toast — render the issues inline in the close dialog with deep links to each blocked entity.

### Pagination + search

List endpoints use skip/limit style pagination with optional `name` search. TanStack Query's `placeholderData: keepPreviousData` is the right pattern for smooth table paging; generated hooks support this via options.

### Phase 6.5 is not built

Several manager-facing concepts (required documents, CPRs with RFA/RFP sub-flows, DEP filings, expected entities, project templates) are designed in the backend roadmap but not yet implemented. The frontend plan treats these as **optional feature flags**: design the screens such that their absence degrades gracefully (hide the tab/section if the endpoint 404s).

---

## Architecture principles

These shape every decision below. Skim before each session.

1. **Config-driven admin CRUD, hand-crafted manager screens.** Admin pages are repetitive — parameterize them. Manager pages carry the real UX weight — build them bespoke per task.
2. **One task per screen in the manager portal.** No 40-field edit forms. Every action is its own focused page or modal.
3. **All server state through TanStack Query.** Never store API responses in Zustand or component state. Cache invalidation is the routing mechanism — master it early.
4. **Every entity combobox supports inline create.** A user staring at a combobox with no matching options should be able to create the missing entity in a modal without losing their form context.
5. **Colocate by feature, not by file type.** `src/features/projects/{routes,components,hooks,types}.ts`, not `src/components/*`, `src/hooks/*`. This is critical for scalability — when feedback lands, you want to change one folder, not grep across five. **Rubric for shared/ vs features/:** a file belongs in `src/shared/` only if it passes all three: (1) _import test_ — no entity-specific type/hook imported; (2) _counterfactual_ — would exist even with only one admin entity; (3) _what-vs-how_ — describes _how_ we render, not _what_ the domain is. "Feature" means domain slice — generic scaffolding never goes under `features/` regardless of size.
6. **Generated API client is the source of truth for types.** Never hand-write a type that could be derived from the schema. Re-run codegen after every backend change.
7. **Forms: schema-first.** Derive zod schemas from the generated types where possible. Manual zod only for cross-field rules the backend validates but schema can't express.
8. **Route-level guards, not component-level.** Authentication + role gating lives in `beforeLoad`. A component that renders is a component that has already passed the gate.
9. **Feature flags for Phase 6.5.** Each unreleased concept gets a `featureFlags.requiredDocs` boolean so the screens can ship dark and light up when the backend arrives.
10. **No premature DRY.** If two admin forms differ by one field, copy. If ten forms differ by one field, extract. Wait for the third duplicate before abstracting.

---

## Documentation conventions

### PATTERNS.md

Create `src/PATTERNS.md` after the generics-extraction session (planned after Employees, ~Session 2.x) once `EntityConfig`, `EntityListPage`, and `EntityFormPage` have been validated against two concrete entities (Schools + Employees). Capture: DataTable column config shape, EntityConfig type, form field patterns, query invalidation patterns. Update it whenever a pattern solidifies or changes.

### Storybook

Add as Session 1.6 (after Session 1.5 fields stabilize). One story per exported shared component. Add component stories during the same session a component is built for Phase 2+. Promoted from "Ongoing" because waiting until polish means context is lost.

### JSDoc / TSDoc

Convention: every exported React component and hook gets a single-line `/** … */` doc comment describing its purpose and any non-obvious props or return values. No multi-paragraph blocks.

### HANDOFF.md updates

Each session must end with an update to `frontend/HANDOFF.md` using this format:

```
**Done:** one bullet per meaningful outcome
**Next:** the next session to run
**Blockers:** anything that needs resolution before next session (or "none")
```

---

## Suggested repo layout

```
src/
├── main.tsx
├── router.tsx                     # tanstack-router setup, root + notFound
├── env.ts                         # Vite env vars, typed
├── featureFlags.ts                # Phase 6.5 toggles
│
├── api/
│   ├── generated/                 # @hey-api/openapi-ts output — do not hand-edit
│   ├── client.ts                  # configured base client + auth interceptor
│   └── queryClient.ts             # TanStack Query singleton + defaults
│
├── auth/
│   ├── store.ts                   # Zustand: user, token, setters
│   ├── guards.ts                  # requireAuth / requireAdmin / requirePermission
│   └── hooks.ts                   # useCurrentUser, useLogin, useLogout
│
├── shared/
│   ├── components/                # layout shells (AppShell), generic data components (DataTable)
│   │   └── ui/                    # shadcn primitives
│   ├── fields/                    # <SchoolCombobox>, <EmployeeCombobox>, ... (may query one entity — still shared because role is reusable field primitive)
│   └── hooks/                     # useFormDialog, useUrlPagination, useUrlSearch, useDebounce, etc.
│                                  # generic EntityListPage / EntityFormPage extracted here after Schools+Employees validate the shape
│
├── features/
│   ├── schools/
│   ├── employees/
│   ├── wa-codes/
│   ├── deliverables/
│   ├── sample-config/
│   ├── sample-batches/
│   ├── contractors/
│   ├── hygienists/
│   ├── users/
│   ├── projects/
│   ├── work-auths/
│   ├── rfas/
│   ├── notes/                     # <NotesPanel> polymorphic
│   └── manager/
│
└── routes/                        # tanstack-router file-based tree (do not hand-edit routeTree.gen.ts)
    ├── __root.tsx
    ├── index.tsx                  # redirects to /projects
    ├── login.tsx
    ├── _authenticated.tsx         # auth guard + AppShell layout
    └── _authenticated/
        ├── projects/
        │   └── index.tsx          # project list ✓
        └── … (all future protected routes)
```

> **Current state:** Migration complete. All components live under `src/shared/components/`. Import alias is `@/` throughout — `@/components/*` resolves to `src/shared/components/*` via tsconfig paths.

---

## Phase 0 — Foundations

- [x] **Session 0.1** — Tooling and API client generation
  - `@hey-api/openapi-ts` + TanStack Query/Router/Form, zod, react-hook-form, zustand installed
  - Generated client in `src/api/generated/`; `pnpm dlx @hey-api/openapi-ts` regenerates it
  - `src/api/client.ts` injects bearer token; `src/api/queryClient.ts` configured

- [x] **Session 0.2** — Auth skeleton
  - `src/auth/store.ts` — Zustand store with `user`, `token`, `setAuth`, `clearAuth`; token persisted to `localStorage`
  - `src/auth/hooks.ts` — `useLogin`, `useLogout`, `useCurrentUser`, `useIsAuthenticated`
  - Login mutation manually sends form-encoded body (OAuth2 password flow)
  - 401 interceptor clears auth and redirects to `/login`

- [x] **Session 0.3** — Routing and guards
  - `src/routes/_authenticated.tsx` — pathless layout route; `beforeLoad` guards all child routes; renders `AppShell` with `<Outlet />`
  - `src/routes/login.tsx` — public; redirects to `/` if already authenticated; uses `Field`/`FieldGroup`/`FieldError` + `standardSchemaResolver`
  - `src/routes/index.tsx` — `beforeLoad` redirects to `/projects`

- [x] **Session 0.4** — Layout shell _(simplified vs original plan)_
  - `src/shared/components/AppShell.tsx` — top nav with app name, Projects link, username, sign-out
  - Single shell for now (no AdminShell / ManagerShell split yet — deferred until admin/manager routing split is built)

- [ ] **Session 0.5** — Testing infrastructure
  - Install: `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`
  - `vitest.config.ts` — jsdom environment, globals: true, setupFiles pointing to `src/test/setup.ts`
  - `src/test/setup.ts` — imports `@testing-library/jest-dom` matchers
  - Smoke test: router renders without crashing
  - Convention: test files live as `*.test.tsx` siblings inside the same feature folder as the component they test

---

## Phase 1 — Shared primitives

- [x] **Session 1.1** — Project list page _(pulled forward from Phase 3)_
  - `src/routes/_authenticated/projects/index.tsx` — table with Project #, Name, Schools columns; `name_search` wired to search input; loading skeleton + empty state
  - No status column (deferred until dashboard endpoints exist)
  - Test: table renders rows; empty state appears on empty response; search input debounces

- [x] **Session 1.2** — Form primitives + field comboboxes
  - `src/lib/form-errors.ts` — `applyServerErrors<T>` maps FastAPI 422 `detail[]` onto RHF `setError`
  - `src/shared/hooks/useDebounce.ts` — `useDebounce<T>(value, delayMs)`
  - `src/shared/fields/SchoolCombobox.tsx` — server-side search, debounced 250ms
  - `src/shared/fields/EmployeeCombobox.tsx` — full list fetched once, client-side filter
  - `useFormDialog()` — deferred; build when first needed by a concrete form

- [x] **Session 1.3** — DataTable primitive
  - `src/shared/components/DataTable.tsx` — generic `<DataTable<TData>>` on TanStack Table v8; `manualPagination: true`; loading skeleton, empty, and error slots; pagination controls hide during non-data states
  - `src/shared/hooks/useUrlPagination.ts` — `useUrlPagination(defaultPageSize?)` syncs `PaginationState` ↔ `page`/`pageSize` URL params; `useSearch({ strict: false })` for route-agnostic reads
  - `src/shared/hooks/useUrlSearch.ts` — `useUrlSearch(param?)` returns `[value, setValue]`; setValue resets `page` to prevent stale offsets
  - Projects list migrated to use `<DataTable>` + `useUrlSearch` + `useUrlPagination`; `pageCount={1}` until backend wraps list responses with a total
  - `DataTable` lives in `src/shared/components/` (roadmap folder diagram updated to match)

- [x] **Session 1.4** — Schools admin _(generics deferred; build concrete first)_
  - **Why deferred:** no consumer existed for generics; principle #10 says wait for the third duplicate. Schools + Employees will reveal the real shape.
  - `src/features/schools/SchoolsListPage.tsx` — list with search, real skip/limit pagination, "Import CSV" button; columns: code, name, borough, address; `onRowClick` navigates to detail
  - `src/features/schools/SchoolImportDialog.tsx` — file input, calls `POST /schools/batch/import`, invalidates list query, shows created count in toast
  - `src/features/schools/SchoolDetailPage.tsx` — read-only display of all school fields
  - `src/shared/hooks/useFormDialog.ts` — `useFormDialog(onClose?)` returns `{ open, setOpen, onOpenChange }` ✓
  - Routes: `_authenticated/admin.tsx` (layout + `is_admin` guard), `admin/schools/index.tsx`, `admin/schools/$schoolId.tsx`
  - **Note on Schools API:** backend has no individual create/update/delete — only list, get-by-identifier, and CSV batch import. Admin pages are read-only + import only.
  - Test: list paginates correctly (real `total` from API); import dialog resets on close; detail page renders all fields

- [ ] **Session 1.5** — Notes panel (polymorphic)
  - `<NotesPanel entityType entityId>` — threaded notes, create, reply, resolve
  - System notes (`note_type != null`): distinct visual treatment, no resolve button
  - Replies collapse/expand
  - Test: system note hides Resolve button; reply thread expands/collapses; new note form submits and invalidates query

- [ ] **Session 1.6** — Storybook setup
  - Install and configure Storybook for Vite + React
  - One story per exported shared component (DataTable, NotesPanel, field comboboxes; EntityListPage/FormPage once extracted in Session 2.2)
  - Convention going forward: new shared components get a story in the same session they are built

---

## Phase 2 — Admin CRUD (simple entities)

- [ ] **Session 2.1** — Employees _(second concrete entity; validates generics shape)_
  - Build like Schools was built in Session 1.4: concrete feature slice, no generics yet
  - Individual create/edit/delete (Employees has full CRUD unlike Schools)
  - Nested `employee_roles` (time-bound) — employee detail gets a **Roles** tab
  - Date-overlap validation is backend-side; surface 422s cleanly
  - Test: create form validates required fields; Roles tab renders; date-overlap 422 surfaces on the correct field

- [ ] **Session 2.2** — Extract generics + retrofit _(DRY when two concrete entities exist)_
  - Extract `EntityListPage`, `EntityFormPage`, `EntityFormDialog` from Schools + Employees patterns
  - These live in `src/shared/components/` (pass the shared/ rubric — no entity imports, generic over `TData`)
  - Retrofit Schools and Employees to use the extracted components
  - Create `src/PATTERNS.md` now that the shapes are stable
  - Test: retrofitted pages render identically; PATTERNS.md documents the column config shape, form field patterns, query invalidation

- [ ] **Session 2.3** — Contractors, hygienists, WA codes, deliverables
  - `WaCode.level` (`project` | `building`) is immutable once in use — read-only in edit form when codes have linked records
  - Deliverables: **Triggers** sub-section via multi-select of WA codes
  - Test: WaCode level field is read-only when codes have linked records; deliverable triggers multi-select saves correctly

- [ ] **Session 2.4** — Users, roles, permissions
  - Password reset as a separate row-menu action → dialog
  - Permissions are read-only seed data; expose as reference table
  - Test: password reset dialog opens from row menu; permissions table is read-only

- [ ] **Session 2.5** — Sample type config
  - Master-detail layout: sample type on left, subtypes/unit types/turnaround/required-roles/WA-codes in right tabs
  - Test: selecting sample type loads its subtypes; `<SampleUnitTypeSelect>` filters by sampleTypeId

- [ ] **Session 2.6** — Sample batches (admin corrections)
  - Test: discard action requires a reason; discarded batch shows visual distinction

---

## Phase 3 — Admin projects

- [ ] **Session 3.1** — Project list + filters _(basic version built in Session 1.1; this session adds filters, manager/school/locked filters, column for current manager + contractor)_
  - Test: filter by locked status shows only locked/unlocked rows; manager filter narrows results

- [ ] **Session 3.2** — Project create + core edit
  - Create wizard: project number (regex-validated), name, manager, schools
  - `project_number` immutable after create — enforce in UI
  - Test: project_number field is read-only in edit mode; regex validation rejects bad formats

- [ ] **Session 3.3** — Schools, contractors, hygienists, managers tabs
  - Four link-table editors; 409 on unlinking a school with downstream records
  - Test: 409 on school unlink surfaces inline error with context, not a generic toast

- [ ] **Session 3.4** — Work auth + WA codes tab
  - Project-level and building-level code sub-tables — do not merge
  - Test: project-level and building-level tables render separately; building-level SchoolSelect filters to linked schools

- [ ] **Session 3.5** — RFAs tab
  - RFA history + create (disabled if pending RFA exists); approve/reject/withdraw; invalidate deliverable queries on approval
  - Test: create button disabled when pending RFA exists; approval invalidates deliverable cache

- [ ] **Session 3.6** — Deliverables tab
  - Two tables (project-level + building-level); inline status edit; guard derived `sca_status` values as read-only
  - Test: first three sca_status values render read-only with "auto" hint; internal_status "blocked" requires notes

- [ ] **Session 3.7** — Time entries tab
  - Filter by employee, date range; row expansion shows linked batches
  - Test: row expansion reveals linked sample batches; assumed entry shows "system" badge

- [ ] **Session 3.8** — Sample batches tab
  - Grouped under time entries; discard action with reason
  - Test: discard requires a reason field; system-created batches show badge and hide edit controls

- [ ] **Session 3.9** — Status + blocking issues panel
  - Right-rail panel from `GET /projects/{id}/status`; "Close project" button → 409 renders `blocking_issues[]` inline
  - Test: 409 from close renders blocking issues with deep links, not a toast; panel reflects live status

- [ ] **Session 3.10** — Notes tab
  - Wrap `<NotesPanel entityType="project" entityId={projectId} />` as its own tab
  - Test: delegates correctly to NotesPanel; tab navigates without remounting panel

---

## Phase 4 — Manager portal

- [ ] **Session 4.1** — Manager dashboard _(get real-manager feedback before continuing Phase 4)_
  - Cards: attention-needed, outstanding deliverables, unresolved blockers, recent activity
  - Client-side N+1 synthesis until Phase 7 dashboard endpoints exist — document the known limitation
  - Test: cards render with mocked data; attention-needed card shows correct count

- [ ] **Session 4.2** — Project workspace layout
  - Tabs are verbs: "Log time", "Record samples", "Update deliverables", "Add note", "Close project"
  - Test: each tab renders its section without crashing; route guard redirects non-managers

- [ ] **Session 4.3** — Log time (focused task)
  - 422 overlap → conflicting entry as clickable card, not a toast
  - Test: 422 response renders conflicting entry card with link; valid submission invalidates time-entries query

- [ ] **Session 4.4** — Record samples (quick-add)
  - Wraps `POST /lab-results/batches/quick-add`; times are optional
  - Test: form submits without times; successful quick-add invalidates both time-entries and batches queries

- [ ] **Session 4.5** — Update deliverables
  - Derived `sca_status` values read-only with info tooltip
  - Test: derived sca_status picker is disabled with tooltip; manual status saves correctly

- [ ] **Session 4.6** — Notes and blockers
  - Filter chips: Blocking only / My notes / System notes
  - Test: filter chip hides/shows correct note subsets; system filter hides manual notes

- [ ] **Session 4.7** — Close project
  - Dedicated page; confirm button disabled until blocking issues is empty
  - Test: confirm button disabled when blocking issues exist; 409 body renders issues with deep links

- [ ] **Session 4.8** — Conflict resolution UX
  - Side-by-side comparison of overlapping time entries with keep/edit/delete per pair
  - Test: both entries render side-by-side; keep/edit/delete actions call correct mutations

---

## Phase 5 — Polish

- [ ] **Session 5.1** — Error + loading + empty states audit
- [ ] **Session 5.2** — Optimistic updates audit
- [ ] **Session 5.3** — Accessibility pass
- [ ] **Session 5.4** — Responsive pass (manager must work on tablet)
- [ ] **Session 5.5** — Toast + confirm dialog conventions
- [ ] **Session 5.6** — Feature-flag scaffolding for Phase 6.5

---

## Ongoing — not a phase

- Regenerate the API client after every backend change (`pnpm dlx @hey-api/openapi-ts` with backend running)
- Storybook — add when shared field components stabilize and feedback cycles pick up
- Error monitoring — Sentry or equivalent before first non-dev deploy

---

## Session sequencing

1. Phase 0 complete.
2. Phase 1 in sequence (primitives build on each other).
3. Phase 2 can parallelize after 2.1 sets the pattern.
4. Phase 3 mostly sequential; tabs (3.3–3.8) can parallelize once 3.1 + 3.2 are solid.
5. **Get real-manager feedback after Session 4.1 before continuing Phase 4.**
6. Phase 5 is ongoing background work.

---

## Feedback adjustment plan

Each manager task screen is a single file in `features/manager/` — replacing it is a rewrite of one file. Dashboard cards are data-driven — adding/removing/reordering is a one-line change. No manager-side component is generalized until it appears in three places.
