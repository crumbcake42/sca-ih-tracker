# Session Handoff — Frontend

## Current State

**Phase 0 complete. Sessions 1.1 through 1.5 complete. Structural refactor complete.** Three-tier layout is live, dead code deleted, `src/shared/` flattened, feature api/ wrappers created, pages layer introduced, auth guard upgraded to async token validation, role-router at `/` added. Polymorphic `<NotesPanel>` primitive built.

## What Was Done This Session (Session 1.5 — NotesPanel)

**Done:**

- Created `src/features/notes/api/notes.ts` — re-export wrapper: `listNotesOptions`, `listNotesQueryKey`, `createNoteMutation`, `createNoteReplyMutation`, `resolveNoteMutation`
- Created `src/features/notes/components/NoteComposer.tsx` — top-level note form (body + is_blocking checkbox, zod + standardSchemaResolver, applyServerErrors on 422)
- Created `src/features/notes/components/ResolveNoteDialog.tsx` — resolve dialog requiring mandatory resolution_note
- Created `src/features/notes/components/NoteItem.tsx` — single note row with system/blocking/resolved badges, inline reply form, collapsible replies disclosure, Resolve dialog integration; system notes omit Resolve button; resolved notes hide action row
- Created `src/features/notes/components/NotesPanel.tsx` — top-level panel; query + loading skeleton + empty state + NoteComposer above list
- `pnpm check` and `tsc --noEmit` clean

**Next:** Session 1.6 — Storybook setup (install + one story per exported shared component; NotesPanel story included)

**Blockers:** Session 0.5 (vitest + RTL infra) is still pending — notes tests deferred until that infra lands

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

## Next Step

**Session 1.5 — Notes panel.**

Build `<NotesPanel entityType entityId>` in `src/features/notes/components/NotesPanel.tsx`. Key constraints from ROADMAP.md:

- System notes (`note_type != null`) get distinct visual treatment and no Resolve button
- Replies are one level deep; collapse/expand
- One component serves all four entity types (`project` | `time_entry` | `deliverable` | `sample_batch`)
- Wrap `listNotesNotesEntityTypeEntityIdGetOptions` etc. under `src/features/notes/api/notes.ts` before using in the component
