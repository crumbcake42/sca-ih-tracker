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
