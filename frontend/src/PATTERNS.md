# Frontend Patterns

Codifies the conventions established during the structural refactor. Read before building any new feature.

---

## Three-tier layering

```
routes/  →  pages/  →  features/*  →  components/, hooks/, fields/, lib/
```

| Layer             | Location                                                   | Responsibility                                                                         |
| ----------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Shared primitives | `src/components/`, `src/hooks/`, `src/fields/`, `src/lib/` | Generic, domain-free building blocks. shadcn primitives, DataTable, shared hooks.      |
| Features          | `src/features/<domain>/`                                   | Routing-agnostic domain components (take props, emit callbacks) + domain API wrappers. |
| Pages             | `src/pages/<route>/`                                       | URL-bound compositions. Own `getRouteApi`, URL↔state wiring, loader data consumption.  |
| Routes            | `src/routes/`                                              | TanStack Router file-based config only (path, loader, `beforeLoad`, `validateSearch`). |

**Direction is strictly one-way.** Features never import from `pages/` or `routes/`. Pages use `getRouteApi('/path')` and never import `Route` from a route file. Routes import only from `@/pages/` and `@/auth/`.

Enforced via eslint `no-restricted-imports` in `eslint.config.js`.

---

## API wrapper layer

Every feature that talks to the backend owns `src/features/<domain>/api/<domain>.ts`. Call sites (feature components, pages) import query/mutation helpers from this file only.

```ts
// features/schools/api/schools.ts
export {
  listEntriesSchoolsGetOptions as listSchoolsOptions,
  listEntriesSchoolsGetQueryKey as listSchoolsQueryKey,
  importBatchSchoolsBatchImportPostMutation as batchImportSchoolsMutation,
} from "@/api/generated/@tanstack/react-query.gen";
```

**Rules:**

- Feature _components_ and _pages_ never import from `@/api/generated/sdk.gen` or `@/api/generated/@tanstack/**` directly.
- Feature _api/_ wrapper files are the exception — they are the bridge to the generated layer.
- Wrappers use domain-operation names, not HTTP-path names: `listSchoolsOptions`, not `listEntriesSchoolsGetOptions`.
- Wrappers are added just-in-time (when first used), not pre-mapped.
- Composed/imperative operations (multi-step mutations, get-or-create) may import from `sdk.gen` inside the wrapper file.
- Cross-cutting code (`src/auth/store.ts`, `src/auth/api.ts`, `src/lib/`) is exempt and may import from `@/api/generated/` directly.

---

## Types policy

Any interface representing a backend payload **must** be imported from `@/api/generated/types.gen.ts`.

If a type is missing or a generated function returns `unknown`, that is a backend bug — fix the FastAPI response model and regenerate. Do not hand-roll the type.

---

## Routing policy

- `/login` is the only public route. All other routes live under `_authenticated/`.
- `_authenticated.tsx` performs a real async token-validity check (`queryClient.ensureQueryData(currentUserOptions())`). On failure it clears auth and redirects to `/login`.
- `_authenticated/index.tsx` is a `beforeLoad`-only role router: `admin` / `superadmin` → `/admin`, everyone else → `/dashboard`.
- Pages use `getRouteApi('/path')` to access typed search/loader data. Never `import { Route } from '@/routes/...'` — that creates a circular dependency.

---

## DataTable + pagination pattern

`useReactTable` is called with `manualPagination: true` and `pageCount` from the API response (`total ÷ limit`). Route files declare `validateSearch` with `page` / `pageSize` / filter params. `useUrlPagination` and `useUrlSearch` read them via `useSearch({ strict: false })` so they work route-agnostically.

```ts
// In the page component:
const [search, setSearch] = useUrlSearch("search");
const { pagination, onPaginationChange } = useUrlPagination();
```

Column definitions are declared as module-level constants outside the component to avoid re-creating the array on each render.

---

## Form pattern

- Schema-first: derive the zod schema from generated types where possible. Manual zod only for cross-field rules.
- Use `standardSchemaResolver` from `@hookform/resolvers/standard-schema` (not `zodResolver`).
- Use `Field` / `FieldLabel` / `FieldError` / `FieldGroup` from `@/components/ui/field` (no shadcn `form` component in `radix-lyra` style).
- Server errors: `applyServerErrors(error, setError)` from `@/lib/form-errors` maps FastAPI 422 `detail[]` onto RHF `setError`.

---

## Combobox pattern

Both comboboxes use `shouldFilter={false}` on `<Command>` so filtering is handled explicitly (server-side for SchoolCombobox, client-side for EmployeeCombobox). Trigger button width matches the popover via `w-[var(--radix-popover-trigger-width)]`. Selecting the already-selected value deselects (toggles to `null`).

---

## Testing

- **Runner:** vitest v3 with jsdom environment. `pnpm test` runs once; `pnpm exec vitest` for watch mode.
- **Globals:** `describe`, `it`, `expect`, `vi`, `beforeEach`, `afterEach` are available without imports (configured in `vitest.config.ts`).
- **jest-dom:** matchers like `toBeInTheDocument()`, `toHaveTextContent()`, `toBeDisabled()` are available without imports (loaded in `src/test/setup.ts`).
- **Location:** test files live as `*.test.tsx` (or `.test.ts`) siblings inside the same feature or component folder. `src/test/` is for infrastructure only (setup, helpers, smoke test).
- **`renderWithProviders`:** import from `@/test/renderWithProviders`. Wraps children in a fresh `QueryClient` (retries off, gcTime 0). Use for any component that calls `useQuery` / `useMutation`. Add router wrapping to this helper when the first router-aware test is written.
- **Mock strategy:** prefer real in-memory data (pass props); use `vi.fn()` for callbacks; defer MSW / network mocking until a test genuinely needs it.
- **`createTestQueryClient`:** import from `@/test/queryClient`. Shared by both `renderWithProviders` and the Storybook preview decorator — retries off, gcTime 0.
- **Vitest workspace:** `pnpm test` runs the `unit` project (jsdom). `pnpm test:stories` runs the `storybook` project (Playwright — requires `pnpm exec playwright install` on first use).

---

## Entity admin list pattern

`EntityListPage<T>` (`src/components/EntityListPage.tsx`) is the standard layout for all admin list screens. It owns `useUrlSearch` + `useUrlPagination`, runs the list query, and renders a Card-wrapped `DataTable` with a header (title + search input + `actions` slot).

**Usage:**

```tsx
// Module-scope column definitions (avoid recreating on every render)
const columns: ColumnDef<Employee>[] = [ ... ];

// In the page component:
<EntityListPage<Employee>
  title="Employees"
  columns={columns}
  queryOptions={listEmployeesOptions}          // pass the factory directly
  searchPlaceholder="Search employees…"
  emptyMessage="No employees found."
  actions={<Button size="sm" onClick={...}>Add employee</Button>}
  onRowClick={(emp) => void navigate({ to: "...", params: { ... } })}
/>
```

**`queryOptions` contract:** the factory must accept `options?: { query?: { search?, skip?, limit? } }` and return an object with `queryKey` and `queryFn` whose data type extends `Paginated<T> = { items: T[]; total: number; skip: number; limit: number }`. All generated `listXxx Options` factories satisfy this — pass them directly with no cast.

**Why `QueryFunction<TPageData, never, never>`:** The code generator stamps `queryFn` with a specific mutable tuple as `TQueryKey`. The generic `QueryKey = readonly unknown[]` is incompatible with that specific tuple in the contravariant `QueryFunctionContext` parameter. Using `never` for `TQueryKey` sidesteps this: `never` is assignable to _any_ type, so any specific-key `QueryFunction` satisfies `QueryFunction<TPageData, never, never>` — but the data type check is preserved, so passing `listEmployeesOptions` to `EntityListPage<School>` is still a compile error. The one internal cast (`opts.queryFn as QueryFunction<TPageData>`) lives inside `EntityListPage`, not at every call site.

**Column definitions** live at module scope in the page file (or a sibling `columns.ts` when the file grows beyond ~30 lines of column config).

**`actions` slot** is a `ReactNode` rendered to the right of the search input. Keep it lean — one or two buttons. Dialogs triggered from here should have their state managed by `useFormDialog()` in the page, with the dialog rendered as a sibling of `EntityListPage`.

---

## Entity form pattern

`useEntityForm` (`src/hooks/useEntityForm.ts`) encapsulates the create/edit lifecycle shared by all admin entity dialogs: RHF setup, reset-on-open, create/update mutation branching, cache invalidation, and error handling (`applyServerErrors` → toast fallback).

**Usage:**

```tsx
const { form, onSubmit, isPending, isEdit } = useEntityForm({
  entity: employee, // undefined = create mode; defined = edit mode
  open, // drives the reset effect
  schema, // Zod schema for TFormValues
  defaultValues, // used in create mode and on close
  toFormValues, // maps TEntity → TFormValues for edit mode
  createMutationOptions: createEmployeeMutation(),
  updateMutationOptions: updateEmployeeMutation(),
  buildCreateVars: (values) => ({ body: toBody(values) }),
  buildUpdateVars: (values, emp) => ({
    path: { employee_id: emp.id },
    body: toBody(values),
  }),
  invalidateKeys: (emp) =>
    emp
      ? [
          listEmployeesQueryKey(),
          getEmployeeQueryKey({ path: { employee_id: emp.id } }),
        ]
      : [listEmployeesQueryKey()],
  entityLabel: "Employee", // used in toast copy
  onSuccess: () => onOpenChange(false),
});
// Then: <form onSubmit={form.handleSubmit(onSubmit)}>...</form>
```

**What the hook does NOT own:** the Dialog shell (Dialog/DialogContent/Header/Footer), the fields JSX, or the dialog-title string. These stay in the entity-specific component — the Dialog markup is short and varies per entity.

**`buildCreateVars` / `buildUpdateVars` split:** keeps the hook agnostic to the generated SDK's path-param shape, which differs per entity. Each caller provides an arrow function that builds the exact variables the mutation expects.

**`invalidateKeys(entity?)` convention:** the hook calls `invalidateKeys(undefined)` on create (no entity ID yet) and `invalidateKeys(existingEntity)` on update. Return `[listQueryKey()]` for create; include the detail key too for update.

**409 / inline-banner escape hatch:** when an entity has a 409 error that should render inline (not as a toast), do NOT use `useEntityForm` for that mutation — handle the error manually via `setError("root.serverError", { message: ... })` after calling `useMutation` directly. See `EmployeeRoleFormDialog` for the reference implementation.

---

## `src/fields/` rationale

Combobox fields and other form-primitive-adjacent components go in `src/fields/` rather than inside a feature, because they are consumed by ≥2 distinct features and are conceptually part of the form-primitive layer (alongside `Input`, `Select`, `Field`).

| Where to put it                     | Rule                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------------------ |
| `src/fields/`                       | Shared across ≥2 features OR form-primitive-adjacent (combobox, date picker, autocomplete) |
| `src/features/<entity>/components/` | Only used inside that one feature                                                          |

**Example:** `EmployeeCombobox` lives in `src/fields/` because it will be consumed by time-entry forms, role-assignment forms, and project-manager pickers — not just the admin employee list. `EmployeeRolesTab` lives in `src/features/employees/components/` because nothing else ever renders it.

---

## Testing strategy

Coverage lives at the layers where logic concentrates; pages mostly compose and don't warrant separate tests.

| Layer                               | What to test                                                                                                                       | What to skip                                                      |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `src/lib/`                          | Pure utilities — all branches                                                                                                      | —                                                                 |
| `src/components/`, `src/hooks/`     | Branching logic: loading/empty/error states, URL wiring, mutation lifecycle (see `useEntityForm.test.ts`)                          | Trivial pass-through props                                        |
| `src/fields/`                       | Server-error UX, debounce behaviour, toggle semantics                                                                              | Snapshot/visual states (Storybook covers those)                   |
| `src/features/<domain>/components/` | Server-error UX (422 field mapping, 409 inline banner), non-obvious invariants (immutable fields in edit mode, cache invalidation) | Happy-path rendering (Storybook), every possible prop combination |
| `src/pages/`                        | Usually none — pages are thin compositions; the composed primitives carry the coverage                                             | —                                                                 |

**Visual states** (loading skeleton, empty, populated, error) are covered by Storybook stories, not by vitest tests. Avoid reproducing the same matrix in both.

**Mock strategy:** mock the feature's API barrel (`vi.mock("@/features/<entity>/api/<entity>", ...)`) and return `{ mutationFn: mockFn }`. Never import from `@/api/generated/` in tests.

---

## Storybook

- **Dev server:** `pnpm storybook` (port 6006). **Build:** `pnpm build-storybook`.
- **Story location:** `*.stories.tsx` sibling to the component file (same convention as `*.test.tsx`). New shared components get a story in the same session they are built.
- **Type imports:** use `@storybook/react-vite` for `Meta`, `StoryObj`, `Decorator`, `Preview` — it re-exports everything from `@storybook/react`.
- **Global QueryClient decorator:** every story is automatically wrapped in a fresh `QueryClient` (via `.storybook/preview.tsx`). No network calls ever hit in stories.
- **Pre-seeding cache:** for components that call `useQuery` internally, use a per-story decorator that calls `queryClient.setQueryData(domainQueryKey(args), fixture)` inside a `useEffect`. Import the `*QueryKey` helper from the feature's `api/` wrapper, not from `@/api/generated/` directly.
- **Naming conflicts:** avoid exporting stories with names that collide with JS globals (`Error`, `Promise`, etc.). Use a display name override: `export const TableError: Story = { name: "Error", ... }`.
- **TanStack Start filter:** `.storybook/main.ts` strips any plugin whose name contains `"tanstack"` in `viteFinal` — same reason vitest uses its own config (SSR transforms break the browser build).
- **shadcn primitive coverage:** all primitives in `src/components/ui/` have stories under `UI/*`. Story files live at `src/components/ui/*.stories.tsx`. The composite showcase is at `src/stories/Showcase.stories.tsx` (`UI/Showcase`). New primitives added via shadcn CLI must ship a story in the same session.
