# SCA IH Tracker — Frontend Roadmap

Companion to `backend/data/roadmap.md`. The backend is feature-complete through Phase 6 (closure + record locking); Phase 6.5 (required-docs silos, expected entities, templates) is planned but not yet implemented.

---

## Stack

- **Vite + React + TypeScript** (project already scaffolded elsewhere)
- **TanStack Router** (file-based routing, route-level loaders + `beforeLoad` guards)
- **TanStack Query** (server state, cache invalidation, optimistic updates)
- **shadcn/ui** + Tailwind (component primitives)
- **react-hook-form + zod** (form state + validation — standard shadcn pairing)
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

| Project-level | Building-level |
|---|---|
| `work_auth_project_codes` | `work_auth_building_codes` |
| `project_deliverables` | `project_building_deliverables` |
| `rfa_project_codes` | `rfa_building_codes` |

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
5. **Colocate by feature, not by file type.** `src/features/projects/{routes,components,hooks,types}.ts`, not `src/components/*`, `src/hooks/*`. This is critical for scalability — when feedback lands, you want to change one folder, not grep across five.
6. **Generated API client is the source of truth for types.** Never hand-write a type that could be derived from the schema. Re-run codegen after every backend change.
7. **Forms: schema-first.** Derive zod schemas from the generated types where possible (`zod-openapi` or a thin adapter). Manual zod only for cross-field rules the backend validates but schema can't express.
8. **Route-level guards, not component-level.** Authentication + role gating lives in `beforeLoad`. A component that renders is a component that has already passed the gate.
9. **Feature flags for Phase 6.5.** Each unreleased concept gets a `featureFlags.requiredDocs` boolean so the screens can ship dark and light up when the backend arrives.
10. **No premature DRY.** If two admin forms differ by one field, copy. If ten forms differ by one field, extract. Wait for the third duplicate before abstracting.

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
│   ├── components/                # buttons, dialogs, layout shells, empty states
│   ├── forms/                     # <Form>, <FormField>, <FormError>, wrappers
│   ├── fields/                    # <SchoolCombobox>, <EmployeeCombobox>, ...
│   ├── tables/                    # <DataTable>, pagination, filter bar
│   └── hooks/                     # useDebouncedValue, useBreakpoint, etc.
│
├── features/
│   ├── entity-crud/               # generic EntityListPage / EntityFormPage + config types
│   ├── schools/                   # config object + any overrides
│   ├── employees/
│   ├── wa-codes/
│   ├── deliverables/
│   ├── sample-config/             # lab_results config tables
│   ├── sample-batches/
│   ├── contractors/
│   ├── hygienists/
│   ├── users/
│   ├── projects/                  # admin projects (complex, bespoke)
│   ├── work-auths/
│   ├── rfas/
│   ├── notes/                     # <NotesPanel> polymorphic
│   └── manager/                   # entire manager portal lives here
│
└── routes/                        # tanstack-router file-based tree
    ├── __root.tsx
    ├── login.tsx
    ├── _auth.tsx                  # requireAuth
    ├── _auth/
    │   ├── index.tsx              # redirect to /admin or /manager by role
    │   ├── _admin.tsx             # requireAdmin
    │   ├── _admin/
    │   │   ├── schools.tsx
    │   │   ├── schools.$id.tsx
    │   │   ├── projects.tsx
    │   │   ├── projects.$id.tsx
    │   │   └── … (one route per admin entity)
    │   ├── _manager.tsx
    │   └── _manager/
    │       ├── index.tsx          # dashboard
    │       ├── projects.$id/      # project workspace (tabbed)
    │       ├── log-time.tsx
    │       ├── add-batch.tsx
    │       └── …
```

---

## Phase 0 — Foundations

Set up everything every later session depends on. Do not skip the smoke tests; a login that "works" but doesn't set the auth header will break every subsequent session.

### Session 0.1 — Tooling and API client generation

- Install `@hey-api/openapi-ts`, `@tanstack/react-query`, `@tanstack/react-router`, `zod`, `react-hook-form`, `@hookform/resolvers`, `zustand`.
- Install shadcn CLI; init with Tailwind already wired; add: `button`, `input`, `label`, `form`, `dialog`, `dropdown-menu`, `command`, `popover`, `select`, `checkbox`, `table`, `tabs`, `toast`, `badge`, `card`, `skeleton`.
- Add `npm run gen:api` script pointing at `http://localhost:8000/openapi.json`. Configure `@hey-api/openapi-ts` to emit: client (`fetch` or `axios`), types, and `@tanstack/react-query` hooks. Output to `src/api/generated/`. Commit output.
- `src/api/client.ts`: configure base URL from env var, inject bearer token from auth store.
- `src/api/queryClient.ts`: `QueryClient` with `staleTime: 30s`, `retry: (failureCount, error) => error.status !== 401 && failureCount < 2`.
- `README.md` addition: how to regenerate the client, when to commit.

**Smoke test:** hit `GET /` through the generated client and render the result on a blank page.

### Session 0.2 — Auth skeleton

- `src/auth/store.ts`: Zustand store — `{ user: User | null, token: string | null, setAuth, clearAuth }`. Persist token to `localStorage`.
- `src/auth/hooks.ts`: `useLogin()` — wraps the token mutation but translates the form-encoded OAuth2 body correctly (the generated client may need a manual override; document this). On success, fetch `/users/me` and stash both.
- `useLogout()` — clears store, invalidates the entire query cache, navigates to `/login`.
- `useCurrentUser()` — `useQuery(['me'])` against `/users/me`; single source of truth for "who am I" throughout the app.
- Auth interceptor on the API client: read token from store on each request; on 401, clear auth and redirect to login.

**Smoke test:** log in as seeded admin; confirm token persists across reload; log out clears state.

### Session 0.3 — Routing and guards

- `src/auth/guards.ts`: `requireAuth`, `requireAdmin`, `requirePermission(name)` — all returning redirect descriptors compatible with TanStack Router's `beforeLoad`.
- Route tree skeleton per layout above: `_auth.tsx` runs `requireAuth`; `_admin.tsx` runs `requireAdmin`.
- `/login` — minimal form, zod validation, calls `useLogin`, shows inline error on 401.
- `/` at authenticated root redirects to `/admin` (if admin role) or `/manager`.
- Admin-view toggle: a button in the admin shell that navigates to `/manager` (and vice-versa if the user is also an admin). No role-bypass — the admin just uses the manager UI, read and write semantics are unchanged.

**Smoke test:** unauthenticated visit to `/admin/schools` lands on `/login?redirect=/admin/schools`; a manager hitting `/admin/*` is redirected to `/manager` with a toast.

### Session 0.4 — Layout shells

- `<AdminShell>` — sidebar nav listing admin entity sections; top bar with user menu + view toggle + logout.
- `<ManagerShell>` — **intentionally sparser**: top bar with user menu + logout, main content full-width. Sidebar nav added only if the dashboard demands it.
- Empty-state placeholder pages for every admin route so the nav tree is fully navigable with no 404s.

**Deliverable at end of Phase 0:** you can log in, see the admin shell, toggle to the manager shell, visit every route without crashing, and log out.

---

## Phase 1 — Shared primitives

These are the bricks every later phase uses. Build them deliberately; rushing here compounds into refactor pain later.

### Session 1.1 — Form primitives

- `<Form>` wrapper around react-hook-form + shadcn `<Form>`: `useForm` config baked in, handles submit/reset/error.
- `<FormField name label description>` renders label + control slot + error message consistently.
- Server-error adapter: a helper that maps FastAPI 422 responses (`detail: [{loc: [...], msg, type}]`) onto react-hook-form `setError` calls so field-level validation messages come straight from the backend.
- `<FormActions>` with consistent Submit + Cancel + Save-and-add-another buttons.
- `useFormDialog()` hook: opens a form inside `<Dialog>`, handles close-on-success, returns a promise resolving to the created entity. This is the primitive that powers inline-create everywhere.

### Session 1.2 — Field components for every entity reference

One component per FK relationship that appears in more than one form. Each wraps shadcn `Command` + `Popover` with async search via TanStack Query.

- `<SchoolCombobox>`, `<EmployeeCombobox>`, `<ContractorCombobox>`, `<HygienistCombobox>`, `<WaCodeCombobox>`, `<SampleTypeSelect>`, `<SampleSubtypeSelect sampleTypeId>`, `<SampleUnitTypeSelect sampleTypeId>`, `<TurnaroundOptionSelect sampleTypeId>`, `<UserCombobox>`, `<EmployeeRoleSelect employeeId>`
- Every combobox accepts an optional `createForm` prop. When present, the dropdown shows a "+ Create new…" row that opens the entity's form in a dialog (via `useFormDialog`), invalidates the list query on success, and auto-selects the new entity.
- Each has a narrow `value`/`onChange` contract that plugs directly into `<FormField>`.

**Non-obvious:** the backend's search endpoints use a `name` query param (plus pagination). Debounce the input ~250ms. Pre-fetch the first page on mount so the dropdown isn't empty when first opened.

### Session 1.3 — DataTable primitive

- `<DataTable columns data pagination filters>` built on TanStack Table; shadcn `<Table>` for the DOM.
- URL-synced pagination + filters (TanStack Router's search params). Back button must restore table state.
- Empty state, loading skeleton, error state — mandatory slots.
- Row click → navigate to detail route.

### Session 1.4 — EntityListPage + EntityFormPage

Generic pages driven by an `EntityConfig<T>` object:

```ts
type EntityConfig<T> = {
  name: string;                              // "School"
  namePlural: string;                        // "Schools"
  basePath: string;                          // "/admin/schools"
  queries: {
    list: UseQueryHook<T[]>;
    detail: (id: number) => UseQueryHook<T>;
    create: UseMutationHook<T, CreateInput>;
    update: UseMutationHook<T, UpdateInput>;
    delete: UseMutationHook<void, number>;
  };
  list: {
    columns: ColumnDef<T>[];
    filters?: FilterConfig[];
    searchable?: boolean;
  };
  form: {
    schema: ZodSchema;
    defaultValues: Partial<T>;
    fields: FieldSpec[];                     // ordered list of {name, component, props}
  };
};
```

- `<EntityListPage config>` renders the list page for any entity.
- `<EntityFormPage config mode="create"|"edit">` renders the form page.
- `<EntityFormDialog config>` is the same form in a dialog — the primitive the comboboxes use for inline create.

**Resist over-abstracting field specs.** A field is `{name, label, component, componentProps}`. Complex validation stays in the zod schema. If an entity needs a layout the generic can't express, that entity gets its own hand-written page and doesn't use this scaffold — that's fine. The generic is for 80% of the admin CRUD, not 100%.

### Session 1.5 — Notes panel (polymorphic)

- `<NotesPanel entityType entityId>` — renders threaded notes, create form, reply form, resolve action.
- Uses the `/notes/{entity_type}/{entity_id}` endpoints.
- System notes (has `note_type`) get a distinct visual treatment and no resolve button.
- Blocking notes get a "blocking" badge.
- Replies collapse/expand.

---

## Phase 2 — Admin CRUD (simple entities)

One session per entity (or small cluster). Each session is a copy-paste exercise after Session 2.1 establishes the pattern.

### Session 2.1 — Schools (pattern-setter)

Build the `EntityConfig` for schools; wire up `/admin/schools` list and detail routes; verify filters, pagination, create, edit, delete all round-trip; verify CSV batch import modal.

This session sets the template. The next sessions are 80% ctrl-C.

### Session 2.2 — Employees + employee roles

Employees have nested `employee_roles` (time-bound) — the employee detail page gets a **Roles** tab that is its own sub-table with its own add-role dialog.

Important: roles have `start_date` + `end_date` (nullable). Date-overlap validation is backend-side; surface 422s cleanly. Role type determines which sample types the employee can collect — relevant downstream.

### Session 2.3 — Contractors, hygienists, WA codes, deliverables

Three essentially-identical CRUD setups. Bundle them into one session.

Non-obvious: `WaCode.level` (`project` | `building`) is immutable once the code is in use. The edit form should read-only this field when the code has any linked records.

Deliverables include a **Triggers** sub-section — managed via `POST/DELETE /deliverables/{id}/triggers`. Admin UI surfaces this as a multi-select of WA codes.

### Session 2.4 — Users, roles, permissions

- `/admin/users` — standard CRUD, plus a "Role" combobox. Password reset is a separate action (button in the row menu → dialog).
- `/admin/roles` — list + detail; the detail page shows the role's permissions as a multi-select.
- Permissions are effectively read-only seed data; expose them as a reference table, not editable.

### Session 2.5 — Sample type config

The lab-results config layer: sample types, subtypes, unit types, turnaround options, required roles, WA codes. Admin CRUD under `/admin/sample-config`.

**UX note:** present this as a master-detail: pick a sample type on the left, edit subtypes/unit types/turnaround/required-roles/WA-codes on the right in tabs. Adding a new sample type should feel like adding a row, not opening a wizard.

### Session 2.6 — Sample batches

Sample batches are data, not config — but admin-side CRUD is still useful for corrections. The manager-side entry flow (quick-add) lives in Phase 4.

Batch validation chain is complex (sample type → subtype scoped to type → unit types scoped to type → inspectors whose role covers the type). Let the backend 422s drive the error messages; do not duplicate validation logic.

---

## Phase 3 — Admin projects

Projects are the complex one. Split into sessions by subsystem.

### Session 3.1 — Project list + filters

- `/admin/projects` list view. Columns: project number, name, current manager, current contractor, linked schools (count), `is_locked`.
- **Do not** compute or display derived status in this list until Phase 7 dashboard endpoints exist. Status belongs on the detail page.
- Filters: by manager, by school, by `is_locked`, free-text search on name + project number.

### Session 3.2 — Project create + core edit

- Create wizard: project number (regex-validated — show pattern hint), name, assign initial manager, link initial schools. Contractor + hygienist links are optional at create and are usually done after.
- Edit form: same core fields except `project_number` (immutable after create — enforce in UI).
- Page layout for project detail: tabs. Core on the overview tab.

### Session 3.3 — Schools, contractors, hygienists, managers tabs

Four link-table editors. Each is a small table with add/remove/reassign actions:

- Schools — add school → creates `project_school_link`. Cannot unlink a school with downstream records (time entries, building-level WA codes, etc.); the backend will 409 — surface that.
- Contractors — `is_current` flag; reassigning the current contractor appends a new link row, does not mutate the old one.
- Hygienist — one at a time.
- Managers — same audit-style append-only reassignment as contractors. `manager_project_assignments` table.

### Session 3.4 — Work auth + WA codes tab

- One WA per project; the tab is either "Create WA" or "Edit WA".
- WA codes split into two sub-tables: project-level and building-level. **Do not merge.**
- Building-level code adder requires picking a linked school first.
- Status badges on every code row.

### Session 3.5 — RFAs tab

- RFA list (history) + "Create RFA" button (only enabled if no pending RFA exists).
- RFA create: pick project codes to add/remove, pick building codes to add/remove with optional `budget_adjustment`.
- RFA resolution action (approve / reject / withdraw) with notes.
- When an RFA is approved, the backend recalculates deliverable statuses — invalidate the project's deliverable queries.

### Session 3.6 — Deliverables tab

- Two tables: project-level and building-level.
- Each row shows the two status tracks (`internal_status` + `sca_status`).
- Inline edit dropdowns; guard against invalid transitions (backend enforces; UI disables illegal options).
- Each row links to its notes panel via a sub-row expansion.

### Session 3.7 — Time entries tab

- List, filter by employee, date range.
- Row expansion shows linked sample batches.
- Delete blocked on active/discarded batches (409 handling).
- Link to the employee detail page.

### Session 3.8 — Sample batches tab

- Grouped under their time entries.
- Batch detail: units, inspectors, notes.
- Discard action (dedicated endpoint) with reason.

### Session 3.9 — Status + blocking issues panel

- Right-rail panel on the project detail page showing `GET /projects/{id}/status` output.
- Blocking issues listed with deep links to the offending entity's tab.
- Status badge in the page header.
- "Close project" button → opens confirmation dialog; on 409, renders returned `blocking_issues[]` inline.

### Session 3.10 — Notes tab + project-level notes panel

Wrap `<NotesPanel entityType="project" entityId={projectId} />` as its own tab. Other tabs can surface entity-scoped notes inline.

---

## Phase 4 — Manager portal

Treat every screen as if the user has never seen a computer. Build slow. Test with real managers between sessions if possible.

### Session 4.1 — Manager dashboard (home)

The single most important screen in the app. Replaces the spreadsheet.

Layout: a vertical stack of labeled cards, each a **pre-computed list** the user would otherwise have to filter for:

- "Projects awaiting your attention" (blocking issues, unconfirmed time entries, pending RFAs on your projects)
- "Projects with outstanding deliverables"
- "Projects with unresolved blockers"
- "Projects closing this week" (placeholder until a close-date concept exists)
- "Recent activity" (last 7 days of your edits)

Each card: title, count, top 3 rows, "View all" link. Cards with zero items say so explicitly ("No projects have outstanding deliverables — nice work.") rather than collapsing.

**Backend gap:** dashboard endpoints (Phase 7) do not exist. For now, synthesize these client-side by calling `/projects/` + `/projects/{id}/status` for each assigned project. This is N+1 and will not scale — but it works for ~30 projects per manager and can be swapped for the real endpoints transparently once they exist. Document the known limitation in the feature README.

References worth citing in code comments:
- GOV.UK Design System (`design-system.service.gov.uk`) — "one thing per page" patterns
- Nielsen Norman Group articles on enterprise task-oriented design
- Caroline Jarrett, *Forms that Work* — specifically chapter on error recovery

### Session 4.2 — Project workspace layout

`/manager/projects/$id` — the manager's view of a single project.

- Header: project name, status badge, quick-facts (current school, manager, WA status).
- Tabbed body, but **tabs are verbs, not nouns**: "Log time", "Record samples", "Update deliverables", "Add note", "Close project". Each tab is a task, not a data view.
- Read-only summary panel on the right rail — shows everything the manager might want to reference without hunting.

### Session 4.3 — Log time (focused task)

The simplest possible time-entry form:

- Pick employee (scoped to employees linked to the current contractor on this project, if any)
- Pick role (scoped to roles active on the chosen date)
- Pick school (scoped to schools linked to this project)
- Enter start + end times (or check "full day" for assumed entries)
- Optional notes
- Submit → success toast + reset to blank form for rapid re-entry

422 overlap → render the conflicting entry as a clickable card ("This overlaps an entry you already made at School X, 9am-11am. View it.") not a toast.

### Session 4.4 — Record samples (quick-add)

Wraps `POST /lab-results/batches/quick-add`. Same structure as Session 4.3 but also collects batch fields. Emphasize that times are optional — they can be filled in later from the daily log.

### Session 4.5 — Update deliverables

List of all deliverables for the project, grouped by project-level vs building-level. Each row: status badges + edit button → focused edit dialog.

Derived `sca_status` values are rendered as read-only with an info tooltip ("This status is set automatically based on WA state").

### Session 4.6 — Notes and blockers

- View all notes on the project + its children in one stream.
- Filter chips: "Blocking only", "My notes", "System notes".
- Creating a note picks the target entity from a dropdown (project / specific time entry / specific deliverable / specific batch).
- Replying and resolving inline.

### Session 4.7 — Close project

Dedicated page, not a modal. Shows:

- Current status (from `/projects/{id}/status`)
- All `blocking_issues[]` grouped by entity type with deep links
- A confirm button **disabled** until blocking issues is empty
- On submit: 409 rendered inline (shouldn't happen if the button was enabled, but handle it); 200 redirects to a success page with a summary of what was locked.

### Session 4.8 — Conflict resolution UX

Dedicated flow for the time-entry overlap case: a screen listing all the manager's conflicting entries with side-by-side comparison and "keep this / edit / delete" actions per pair.

---

## Phase 5 — Polish

### Session 5.1 — Error + loading + empty states audit

Walk every route. Every query should have: loading skeleton, empty state copy, error state with retry.

### Session 5.2 — Optimistic updates audit

Every mutation that can be safely optimistic (status changes, note resolves, simple field edits) should be. Use TanStack Query `onMutate` + rollback on error. Creates and deletes generally should not be optimistic.

### Session 5.3 — Accessibility pass

Keyboard navigation through every admin table and every manager form. ARIA labels on icon buttons. Focus trapping in dialogs (shadcn handles most of this; verify). Color contrast on status badges.

### Session 5.4 — Responsive pass

Admin is desktop-first and that's fine. Manager must work on tablet — air techs in the field. Test every manager screen at 768px wide. One-column stacks, bigger tap targets.

### Session 5.5 — Toast + confirm dialog conventions

Audit every destructive action: must have a named confirmation ("Type the project number to confirm"). Every successful mutation: single consistent toast style.

### Session 5.6 — Feature-flag scaffolding for Phase 6.5

Add `featureFlags.requiredDocs`, `featureFlags.expectedEntities`, `featureFlags.projectTemplates`. Stub the pages behind them. When backend endpoints land, flip the flags and fill in.

---

## Ongoing — not a phase

- **Regenerate the API client after every backend change.** Consider a CI check that fails the build if generated output differs from committed output.
- **Storybook.** Optional but strongly recommended for the shared field components — they're reused enough that visual regression matters. Add only when feedback cycles pick up.
- **Error monitoring.** Sentry or equivalent, wired before the first non-dev deploy. Correlate with backend request IDs once backend adds them.

---

## Session sequencing suggestions

These sessions are designed to be mostly-independent. A reasonable build order:

1. All of Phase 0 in sequence (0.1 → 0.4).
2. Phase 1 in sequence (primitives build on each other).
3. Phase 2 can parallelize after 2.1 sets the pattern — if multiple people are working, fan out 2.2–2.6.
4. Phase 3 is mostly sequential but 3.3–3.8 (the tabs) can parallelize once 3.1 + 3.2 are solid.
5. **Get real-manager feedback after Session 4.1 before continuing Phase 4.** The dashboard is the keystone; if the card set is wrong, everything downstream bends around the wrong pivot.
6. Phase 5 is ongoing background work; allocate to it proportional to how much feedback is landing.

---

## Feedback adjustment plan

Because the manager-side UX is genuinely unknown until real users touch it, structure every manager-side feature so it can be rebuilt cheaply:

- Each task screen is a single file in `features/manager/` — replacing it is a rewrite of one file.
- The dashboard cards are data-driven: cards live in an array; adding/removing/reordering is a one-line change.
- No manager-side component is generalized until it appears in three places. The first two manager screens may look structurally similar but should not share code — duplication is cheaper than premature abstraction when the spec is changing.
- Admin screens are already generic by construction; feedback-driven changes there are typically config tweaks, not rewrites.
