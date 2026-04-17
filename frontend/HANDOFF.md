# Session Handoff — Frontend

## Current State

**Phase 0 complete. Session 1.1 complete.** Project list page is live at `/projects`. Next session is **1.2 — Field comboboxes / form primitives**.

## What Was Done This Session (1.1)

### Created

- `src/routes/_authenticated/projects/index.tsx` — project list at `/projects`. Fetches via `getProjectsProjectsGetOptions`, supports `name_search` query param wired to a search input. Table columns: Project #, Name, Schools (count). Includes loading skeleton and empty state. No status column (status is derived — deferred until dashboard endpoints exist).

### Modified

- `src/routes/index.tsx` — replaced AppShell placeholder with a bare `beforeLoad` redirect to `/projects`.
- `src/components/AppShell.tsx` — both nav links updated from `to="/"` to `to="/projects"`.
- `src/routes/login.tsx` — migrated off the removed `form` component to shadcn `Field` / `FieldGroup` / `FieldError` from `#/components/ui/field`. Switched from `zodResolver` to `standardSchemaResolver` from `@hookform/resolvers/standard-schema` to fix a type overload conflict introduced by zod v4.

## Architecture Notes

### shadcn style is `radix-lyra` — no `form` component

The `form` shadcn component does not exist in this style. Use `Field`, `FieldLabel`, `FieldError`, `FieldGroup` from `#/components/ui/field` with react-hook-form's `register` / `formState.errors` directly:

```tsx
<Field data-invalid={!!errors.fieldName}>
  <FieldLabel htmlFor="fieldName">Label</FieldLabel>
  <Input
    id="fieldName"
    aria-invalid={!!errors.fieldName}
    {...register('fieldName')}
  />
  <FieldError errors={[errors.fieldName]} />
</Field>
```

`FieldError` accepts `errors: Array<{ message?: string } | undefined>` — pass the RHF error object directly in an array.

### Use `standardSchemaResolver` not `zodResolver`

Zod v4 + `@hookform/resolvers` v5 have a type overload conflict when using `zodResolver`. Use `standardSchemaResolver` from `@hookform/resolvers/standard-schema` instead — zod v4 implements the Standard Schema spec natively.

```ts
import { standardSchemaResolver } from '@hookform/resolvers/standard-schema'
// ...
resolver: standardSchemaResolver(myZodSchema)
```

### Route architecture

```
/ (index.tsx)                        — beforeLoad redirects to /projects
/login (login.tsx)                   — public; redirects to / if authenticated
/_authenticated (_authenticated.tsx) — layout: auth guard + AppShell wraps Outlet
/_authenticated/projects/            — project list
```

All future protected routes go under `src/routes/_authenticated/`.

## Next Step

**Session 1.2 — Field combobox components and form primitives.**

Key tasks:

1. Server-error adapter: map FastAPI 422 `detail: [{loc, msg, type}]` responses onto react-hook-form `setError` calls. This is needed by every form that mutates data.
2. `<SchoolCombobox>`, `<EmployeeCombobox>` — the two most immediately needed FK pickers. Each wraps shadcn `Command` + `Popover` with async search via TanStack Query. Debounce ~250ms. Pre-fetch first page on mount.
3. `useFormDialog()` hook — opens a form in a `<Dialog>`, closes on success, resolves to the created entity. Powers inline-create in every combobox.

Notes:

- Combobox components belong in `src/shared/fields/` per the roadmap's suggested layout.
- Each combobox should accept `value` / `onChange` that plugs directly into react-hook-form's `Controller` render prop or `useController`.
- The `createForm` inline-create prop can be deferred to a follow-up session if scope is too large.
