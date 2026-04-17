# Session Handoff — Frontend

## Current State

**Phase 0, Session 0.1 complete.** Tooling and API client are wired up. Next session is **0.2 — Auth skeleton**.

## What Was Done This Session (0.1)

### Installed

- `zod`, `react-hook-form`, `@hookform/resolvers`, `zustand`
- `@hey-api/openapi-ts` (codegen tool)
- `@tanstack/react-query-devtools`
- shadcn/ui (radix-lyra style) with components: button, input, label, form, dialog, dropdown-menu, command, popover, select, checkbox, table, tabs, sonner (toast), badge, card, skeleton

### Created

- `openapi-ts.config.ts` — codegen config; `bundle: true` (no external client-fetch package needed); `runtimeConfigPath: '../client'` wires base URL from our config function
- `.env.local` — `VITE_API_BASE_URL=http://127.0.0.1:8000`
- `src/api/client.ts` — exports `createClientConfig` (called by generated client on init); exports `setTokenGetter` / `getToken` stubs to be wired in Session 0.2
- `src/api/queryClient.ts` — singleton `QueryClient` with `staleTime: 30s`, smart retry (no retry on 401)
- `src/api/generated/` — full OpenAPI client generated from `/openapi.json`; includes `@tanstack/react-query.gen.ts` with typed `queryOptions` and `UseMutationOptions` for every endpoint

### Modified

- `src/router.tsx` — added `setupRouterSsrQueryIntegration({ router, queryClient })` via `@tanstack/react-router-ssr-query`
- `src/routes/__root.tsx` — stripped marketing Header/Footer, updated title to "SCA IH Tracker", added `<Toaster />`
- `src/routes/index.tsx` — replaced marketing content with a smoke test page (hits `GET /`, shows connection status with shadcn Badge + Button)
- `package.json` — added `gen:api` script (`openapi-ts`)

## Non-Obvious Notes for Next Session

### shadcn style is "radix-lyra" (not "default")

This is a newer shadcn preset. Components use Phosphor icons (`@phosphor-icons/react`), not Lucide. When adding icons to UI, import from `@phosphor-icons/react`.

### Auth token injection is a stub

`src/api/client.ts` exports `setTokenGetter(getter)`. In Session 0.2, the Zustand store calls `setTokenGetter(() => useAuthStore.getState().token)` once on app mount. The generated client already calls `createClientConfig` on init, but that only sets the base URL — it does NOT handle per-request auth headers. Per-request auth needs to be added via `client.interceptors.request.use()` on the generated `client` from `src/api/generated/client.gen.ts`.

### `pnpm gen:api` requires the backend running

Backend must be at `http://127.0.0.1:8000`. Run `just api` from the project root first.

### Generated code is in `src/api/generated/` — do not hand-edit

Re-run `pnpm gen:api` after any backend endpoint change. The `output.clean: true` config will delete and regenerate the entire folder.

## Next Step

**Session 0.2 — Auth skeleton.**

Key tasks:

1. `src/auth/store.ts` — Zustand store: `{ user, token, setAuth, clearAuth }`. Persist token to localStorage (SSR-safe: guard `typeof window !== 'undefined'`).
2. Wire `setTokenGetter` into the store: after `setAuth`, call `setTokenGetter(() => store.getState().token)`.
3. Add response interceptor to `client` for 401 → `clearAuth()`.
4. `src/auth/hooks.ts` — `useLogin()` that calls `loginForAccessTokenAuthTokenPost` with **form-encoded body** (NOT JSON — the generated client may need a manual override; the backend uses OAuth2 password flow with `application/x-www-form-urlencoded`).
5. After login success, call `getMeUsersMeGet` to hydrate the user in the store.
6. `useLogout()`, `useCurrentUser()` hooks.

Critical gotcha: `POST /auth/token` must send `Content-Type: application/x-www-form-urlencoded`. Check what the generated `loginForAccessTokenAuthTokenPost` sends — it may default to JSON. If so, override it manually rather than using the generated function.
