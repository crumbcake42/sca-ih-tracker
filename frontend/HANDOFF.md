# Session Handoff — Frontend

## Drift surfaced by Session F regen audit (2026-04-27)

OpenAPI client regenerated against backend post-Session-F (regen sits unstaged in the working tree at the time of writing). Most of the pending-pickup items below landed cleanly, but the audit surfaced backend gaps and FE doc/scope issues that need to be resolved before further work in this area:

**Blocking backend gaps** (also recorded in `backend/HANDOFF.md` "FE regen drift to address"):

1. ~~**Close 409 response is not in the OpenAPI schema.**~~ **RESOLVED (2026-04-28, Phase 6.6 Session A).** `POST /projects/{project_id}/close` now declares `responses={409: {"model": CloseProjectConflictDetail}}`. New schema `CloseProjectConflictDetail`: `{ blocking_issues?: BlockingIssue[]; unfulfilled_requirements?: UnfulfilledRequirement[] }`. Exactly one key is populated per response (blocking notes checked first). Regen the client; the generated error type will now carry both keys typed.
2. ~~**Session 2.3e (Deliverables admin) still blocked**~~ **RESOLVED (2026-04-28, Phase 6.6 Session A).** `POST /deliverables/` (201) and `PATCH /deliverables/{id}` (200) are now implemented. Schema note: the catalog `Deliverable` has **only** `name`, `description`, `level` — **not** `internal_status`/`sca_status`. Those columns live on `ProjectDeliverable`/`ProjectBuildingDeliverable` (per-project rows), not the catalog. The previous note in this file claiming the admin needs four fields was wrong. New `DeliverableCreate` / `DeliverableUpdate` cover exactly the three catalog fields. Duplicate-name collision returns **422** (matches codebase pattern). `level` is immutable after creation — PATCH returns 422 if you try to change it. Both endpoints require `PROJECT_EDIT` permission. Regen the client.
3. ~~**`undismiss` only exists for lab reports.**~~ **RESOLVED (2026-04-28, Phase 6.6 Session B).** `POST /cprs/{id}/undismiss`, `POST /document-requirements/{id}/undismiss`, and `POST /dep-filings/{id}/undismiss` now exist with the same 404/422/409 guards as `POST /lab-reports/{id}/undismiss`. All four silos support dismiss + undismiss symmetrically.
4. ~~**No way to discover valid requirement-trigger types from the schema.**~~ **RESOLVED (2026-04-28, Phase 6.6 Session C).** Two changes: (a) `WaCodeRequirementTriggerCreate.requirement_type_name` is now typed as a `Literal` enum of the six registered handler names — the generated SDK type is no longer `string`; (b) new `GET /requirement-types` endpoint returns `list[RequirementTypeInfo]` with `name`, `events`, `template_params_schema` (JSON Schema), `is_dismissable`, `display_name`. FE can render the requirement-trigger create form dynamically from this. Regen the client.
5. ~~**Duplicated requirement-triggers namespace.**~~ **RESOLVED (2026-04-28, Phase 6.6 Session C).** The `/wa-codes/requirement-triggers` re-mount has been removed. Canonical path is `/requirement-triggers` only (unchanged). The near-duplicate SDK function `createRequirementTriggerWaCodesRequirementTriggersPost` is gone after regen.

**FE-side cleanup before continuing**:

6. **`frontend/CLAUDE.md` is stale** — line 24 says "Notes are polymorphic … four entity types (`project` | `time_entry` | `deliverable` | `sample_batch`)." `NoteEntityType` now has five values; `'contractor_payment_record'` was added. Update the doc and confirm `NotesPanel` is wired up for CPR rows on the new CPR silo UI.
7. **`NoteType` gained `'cpr_stage_regression'`.** Any `NotesPanel` switch on note type (icons/labels/system-badge logic) needs a branch for it. New variant is system-generated.
8. **Deliverables blocker description below is wrong.** It says the create surface needs "name, description, internal_status, sca_status," but `internal_status`/`sca_status` live on `ProjectDeliverable`/`ProjectBuildingDeliverable`, not the catalog `Deliverable` (which has only `name`/`description`/`level`). Reconfirm scope with backend before unblocking and rewrite the entry.
9. **Stale "Next" pointer in Current State.** Session F now unblocks four new silo UIs (DEP filings, lab reports, document requirements, CPRs), the `unfulfilled_requirement_count` badge on the close flow, and the dual-detail close-409 handler. ROADMAP needs re-sequencing — Session 2.3e is no longer the only logical next thing, just still blocked.
10. **`hasConnections(unknown)` cast in `WaCodeFormDialog.tsx`** is now actually removable (`WaCodeConnections` is typed). Quick warm-up task.

**Resolved by this regen** (no further action needed):

- `ProjectStatusRead.unfulfilled_requirement_count`, `UnfulfilledRequirement` schema, `GET /projects/{id}/requirements`
- DEP filings: `DepFilingForm{Read,Create,Update,Connections}`, `ProjectDepFiling{Read,Create,Update,Dismiss}` and all `/dep-filings/...` + `/projects/{id}/dep-filings` endpoints
- Lab reports: `LabReportRequirement{Read,Update,Dismiss}` + `/projects/{id}/lab-reports`, `/lab-reports/{id}/{save,dismiss,undismiss}`
- Document requirements: full CRUD + dismiss surface present; `is_required` removed
- CPRs: full CRUD + dismiss surface present; `is_required` removed; `BlockingIssue` shape unchanged
- Sample batch types lose `is_report`
- `UnfulfilledRequirement` does not carry `requirement_key`
- All six `*Connections` schemas typed
- `GET /work-auths/` paginated (`PaginatedResponseWorkAuth`)

---

## Backend changes pending frontend pickup

**Session F (backend) landed (2026-04-27) — final Phase 6.5 regen. Regenerate the OpenAPI client before the next FE session.**

Changes since last regen (Sessions E0d + E + E2 + F all land together):

- `ProjectStatusRead` has a new field `unfulfilled_requirement_count: int`. Any component reading `ProjectStatusRead` (e.g. project close flow, status badge) should display or act on this count.
- New `UnfulfilledRequirement` schema: `{ requirement_type, project_id, label, is_dismissed, is_dismissable }`.
- New endpoint `GET /projects/{project_id}/requirements` → `list[UnfulfilledRequirement]`. Returns all unfulfilled, non-dismissed requirements across all silos for the project.
- `POST /projects/{project_id}/close` now 409s with `{"unfulfilled_requirements": [...]}` in addition to the existing `{"blocking_issues": [...]}` path. The FE close flow needs to handle both 409 detail shapes.
- CPR blocking notes now appear in `blocking_issues` responses (previously silently dropped). No FE code change needed — the `BlockingIssue` shape is unchanged.
- `ContractorPaymentRecordRead` and `ProjectDocumentRequirementRead` lost `is_required` (Session E0d).
- New Session E schemas: `DEPFilingFormRead/Create/Update`, `ProjectDEPFilingRead/Update/Dismiss`, `ProjectDEPFilingCreate`.
- New Session E endpoints: `/dep-filings/forms/*`, `/dep-filings/{id}`, `/projects/{id}/dep-filings`.
- `SampleBatchRead/Create/Update/QuickAdd` lose `is_report` (Session E2). Migrate any FE code reading or writing `is_report` to the new `GET /projects/{id}/lab-reports` + `PATCH /lab-reports/{id}/save` + `POST /lab-reports/{id}/dismiss` endpoints.
- New `LabReportRequirementRead` schema; new endpoints: `GET /projects/{id}/lab-reports`, `PATCH /lab-reports/{id}/save`, `POST /lab-reports/{id}/dismiss`, `POST /lab-reports/{id}/undismiss`.

---

**Session E0c landed (2026-04-27) — regen OpenAPI client before next FE session.**

- `UnfulfilledRequirementRead` loses `requirement_key` field. FE does not currently consume this field, so no code changes needed — just regen.
- `ContractorPaymentRecordRead.label` value changes: now includes the contractor name (e.g. `"CPR — ACME Corp"` instead of `"CPR — Contractor #7"`). Any FE component that displays this label verbatim now shows the correct contractor name automatically after regen. No schema shape change (still `label: string`).
- `ContractorPaymentRecordRead` and `ProjectDocumentRequirementRead` schema shapes are otherwise unchanged — `label`, `is_fulfilled`, `is_dismissed` still present as same types.
- `POST /requirement-triggers/` now rejects `requirement_type_name` values that don't subscribe to `WA_CODE_ADDED` (e.g. `"deliverable"`, `"contractor_payment_record"`). If FE has any code creating triggers with those types, update to `"project_document"` with `template_params: {"document_type": "<value>"}`.

---

**`*Connections` schemas now typed — regen the OpenAPI client.** Six reference entities (`Contractor`, `Hygienist`, `School`, `Employee`, `Deliverable`, `WACode`) previously returned `unknown` from their `/connections` endpoints. The backend now emits named Pydantic schemas (`ContractorConnections`, `HygienistConnections`, `SchoolConnections`, `EmployeeConnections`, `DeliverableConnections`, `WACodeConnections`) with typed integer counts. After regenerating the client, the `hasConnections(unknown)` cast in `WaCodeFormDialog.tsx` can be removed.

**Add single-item Deliverables endpoints** — need `POST /deliverables/` and `PATCH /deliverables/{id}` to mirror the admin CRUD surface on other entities (name, description, internal_status, sca_status). Current API has list, delete, batch-import, and trigger management but no standalone create/update. Blocks Session 2.3b (Deliverables admin). Regenerate the OpenAPI client after backend ships.

**`GET /work-auths/` is now paginated** — returns `PaginatedResponseWorkAuth` (`{items, total, skip, limit}`). Any FE code reading `response.project_id` directly must migrate to `response.items[0]?.project_id` and guard empty. Not yet audited — check during Phase 3 (Session 3.4 Work Auth tab) or sooner if a consumer is found.

---

## Current State

**Sessions 0.5, 1.1–1.7, 2.1a, 2.1b, 2.1c, 1.5A, 1.5B, 1.5C, 2.2, backend-pickup migration, auth fix, 2.3a, 2.3b, 2.3c, 2.3d, connections-pickup audit, and Session F regen audit complete.**

- All 2.3a–2.3d admin CRUD slices complete.
- OpenAPI client regenerated post-Session F (E0d + E + E2 + F all landed); regen sits unstaged in the working tree pending a standalone commit.
- Drift audit done: most pickup items resolved; 5 backend gaps + 5 FE doc/scope cleanups documented at top of this file and in `backend/HANDOFF.md` "FE regen drift to address."

**Next:** decide what to build first now that the four silo schemas are typed (DEP filings UI, lab reports UI, document requirements UI, CPRs UI, close-flow `unfulfilled_requirement_count` badge + dual-detail 409 handler), and whether to wait on backend for the close-409 schema fix before touching the close gate. Session 2.3e (Deliverables) still blocked. ROADMAP needs re-sequencing.

---

## What Was Done This Session (Session F regen audit + cross-side drift documentation)

**Done:**

- Reviewed unstaged regen of `frontend/src/api/generated/{types.gen.ts,sdk.gen.ts,@tanstack/react-query.gen.ts,index.ts}` against `frontend/HANDOFF.md`'s pending-pickup list.
- Confirmed resolved by the regen: `ProjectStatusRead.unfulfilled_requirement_count`, `UnfulfilledRequirement` schema, `GET /projects/{id}/requirements`, full DEP-filing surface (`DepFilingForm{Read,Create,Update,Connections}`, `ProjectDepFiling{Read,Create,Update,Dismiss}` and their endpoints), full lab-report surface (`LabReportRequirement{Read,Update,Dismiss}` + save/dismiss/undismiss), document-requirement and CPR surfaces with `is_required` removed, sample-batch types with `is_report` removed, `requirement_key` removed, all six `*Connections` typed, `PaginatedResponseWorkAuth`.
- Surfaced drift items (5 backend + 5 FE) in a new "Drift surfaced by Session F regen audit" section at the top of this file: missing 409 schema on close, missing standalone Deliverables CRUD, asymmetric undismiss (only lab reports has it), untyped `requirement_type_name` + `template_params`, duplicated requirement-triggers namespace, stale CLAUDE.md polymorphic-notes count (4 → 5), new `NoteType.cpr_stage_regression` variant, wrong field-list in the deliverables blocker description, stale Next pointer, removable `hasConnections` cast.
- Mirrored the backend-side items into `backend/HANDOFF.md` under a new "FE regen drift to address (audit 2026-04-27)" section so the next backend session picks them up.
- Did not yet stage/commit the regen, update `frontend/CLAUDE.md`, remove the `hasConnections(unknown)` cast, or re-sequence ROADMAP — those are follow-ups for the next session.

**Next:** commit the regen as a standalone "regenerate OpenAPI client (post-Session F)" commit, then decide which silo UI to build first. The `WaCodeFormDialog.tsx` cast cleanup and the `frontend/CLAUDE.md` four-→-five entity-types fix are quick warm-ups.

**Blockers:** see "Drift surfaced by Session F regen audit" at top of file. The close-flow UI cannot be cleanly typed until backend declares `responses={409: ...}` on `POST /projects/{id}/close`. Session 2.3e (Deliverables) still blocked on standalone CRUD endpoints. Other items are workable but require FE-side knowledge of runtime constraints not in the schema.

---

## What Was Done Previously (Connections pickup audit — OpenAPI regen)

**Done:**

- Audited newly regenerated OpenAPI client (`types.gen.ts`, `sdk.gen.ts`) against outstanding pickup items in HANDOFF.
- Confirmed resolved: all six connections endpoints now return typed schemas — `WaCodeConnections`, `DeliverableConnections`, `ContractorConnections`, `HygienistConnections`, `EmployeeConnections`, `SchoolConnections` all typed at `200`. The `hasConnections(unknown)` cast in `WaCodeFormDialog.tsx` is now removable.
- Confirmed still blocked: no standalone `POST /deliverables/` or `PATCH /deliverables/{id}`; `DeliverableCreate`/`DeliverableUpdate` types absent from generated client. Session 2.3e remains blocked.
- Updated HANDOFF: removed resolved connections pickup item, fixed deliverables blocker label (was "2.3b", now correctly "2.3e"), refreshed Current State and 2.3d blockers line.

**Next:** Session 2.3e (Deliverables) — blocked. Can start next session with the `WaCodeFormDialog.tsx` cast cleanup as a warm-up.

**Blockers:** Session 2.3e — backend needs `POST /deliverables/` + `PATCH /deliverables/{id}`.

---

## What Was Done This Session (Session 2.3d — Employee Role Types admin CRUD)

**Done:**

- Built Employee Role Types admin CRUD wired to the admin dashboard and sidebar.
- Created `src/features/employee-role-types/api/employeeRoleTypes.ts` — new canonical barrel for all role-type endpoint wrappers: `listEmployeeRoleTypesOptions/QueryKey`, `getEmployeeRoleTypeOptions/QueryKey` (NEW — was missing), `createEmployeeRoleTypeMutation`, `updateEmployeeRoleTypeMutation`, `deleteEmployeeRoleTypeMutation`.
- Migrated `EmployeeRoleFormDialog.tsx` and its test to import `listEmployeeRoleTypesOptions` from the new barrel; removed the five role-type re-exports from `src/features/employees/api/employees.ts`.
- `EmployeeRoleTypeFormDialog.tsx` — `useEntityForm`-based add/edit dialog; schema has `name` required, `description` optional nullable; empty string → `null` on submit.
- `EmployeeRoleTypeDetail.tsx` — detail card with two `DetailRow`s (name, description); edit/delete buttons; `DeleteConfirmDialog` renders 409 `detail` inline, no toast.
- `src/pages/admin/employee-role-types/{index,detail,loader}.tsx` — custom inline table list page (endpoint returns plain array, not paginated — can't use `EntityListPage`), detail page wrapper, loader.
- `src/routes/_authenticated/admin/employee-role-types/{index,$roleTypeId}.tsx` — file routes. Route tree regenerated via `pnpm exec tsr generate`.
- Enabled Employee Role Types in `nav-items.ts` (new entry with `IdentificationCardIcon`) and `src/pages/admin/index.tsx` dashboard card.
- Tests: `EmployeeRoleTypeFormDialog.test.tsx` (4 tests: create, required-field validation, 422→applyServerErrors, edit prefill); `EmployeeRoleTypeDetail.test.tsx` (1 test: 409 inline, no toast).
- All 37 tests pass; `pnpm tsc --noEmit` and `pnpm check` clean.

**Next:** Session 2.3e (Deliverables) — still blocked by backend.

**Blockers:** Session 2.3e (Deliverables) — backend still needs `POST /deliverables/` + `PATCH /deliverables/{id}`. `WaCodeFormDialog.tsx` cast cleanup — backend needs `WaCodeConnections` response model on `GET /wa-codes/{id}/connections`.

---

## What Was Done This Session (Session 2.3c — Hygienists admin CRUD)

**Done:**

- Built Hygienists admin CRUD wired to the admin dashboard and sidebar.
- `src/features/hygienists/api/hygienists.ts` — full barrel: `listHygienists*`, `getHygienist*`, `createHygienistMutation`, `updateHygienistMutation`, `deleteHygienistMutation`, `getHygienistConnections*`.
- `HygienistFormDialog.tsx` — `useEntityForm`-based add/edit dialog; schema has `first_name`/`last_name` required, `email`/`phone` optional nullable; email coerces empty string to `null` on submit.
- `HygienistDetail.tsx` — detail card with four `DetailRow`s (first name, last name, email, phone); edit/delete buttons; `DeleteConfirmDialog` renders 409 `detail` inline, no toast.
- `src/pages/admin/hygienists/{index,detail,loader}.tsx` — `EntityListPage<Hygienist>` list (Name via `accessorFn`, Email, Phone columns), detail page wrapper, loader.
- `src/routes/_authenticated/admin/hygienists/{index,$hygienistId}.tsx` — file routes with `validateSearch` and loader. Route tree regenerated.
- Enabled Hygienists in `nav-items.ts` and `src/pages/admin/index.tsx` dashboard card.
- Tests: `HygienistFormDialog.test.tsx` (4 tests: create, required-field validation, 422→applyServerErrors, edit prefill); `HygienistDetail.test.tsx` (1 test: 409 inline, no toast).
- All 32 tests pass; `pnpm tsc --noEmit` and `pnpm check` clean.

**Next:** Session 2.3d (Employee Role Types) — unblocked.

**Blockers:** Session 2.3e (Deliverables) — backend still needs `POST /deliverables/` + `PATCH /deliverables/{id}`. `WaCodeFormDialog.tsx` cast cleanup — backend needs `WaCodeConnections` response model on `GET /wa-codes/{id}/connections`.

---

## What Was Done This Session (Session 2.3b — Contractors admin CRUD)

**Done:**

- Built Contractors admin CRUD wired to the admin dashboard and sidebar.
- `src/features/contractors/api/contractors.ts` — full barrel: `listContractors*`, `getContractor*`, `createContractorMutation`, `updateContractorMutation`, `deleteContractorMutation`, `getContractorConnections*`, `importBatchContractorsMutation`.
- `ContractorFormDialog.tsx` — `useEntityForm`-based add/edit dialog; schema has all five fields required (matching `ContractorCreate`); no immutable-field lock (no level equivalent).
- `ContractorDetail.tsx` — detail card with five `DetailRow`s, edit/delete buttons; `DeleteConfirmDialog` renders 409 `detail` inline, no toast.
- `src/pages/admin/contractors/{index,detail,loader}.tsx` — `EntityListPage<Contractor>` list (Name, City, State, Zip code columns), detail page wrapper, loader.
- `src/routes/_authenticated/admin/contractors/{index,$contractorId}.tsx` — file routes with `validateSearch` and loader. Route tree regenerated.
- Enabled Contractors in `nav-items.ts` and `src/pages/admin/index.tsx` dashboard card.
- Fixed 2.3a oversight: WA Codes dashboard card was still `disabled: true` — flipped to active (`to: "/admin/wa-codes"`).
- Tests: `ContractorFormDialog.test.tsx` (4 tests: create, required-field validation, 422→applyServerErrors, edit prefill); `ContractorDetail.test.tsx` (1 test: 409 inline, no toast).
- All 27 tests pass; `pnpm tsc --noEmit` and `pnpm check` clean.

**Next:** Session 2.3c (Hygienists) or 2.3d (Employee Role Types) — both unblocked.

**Blockers:** Session 2.3e (Deliverables) — backend still needs `POST /deliverables/` + `PATCH /deliverables/{id}`. `WaCodeFormDialog.tsx` cast cleanup — backend needs `WaCodeConnections` response model on `GET /wa-codes/{id}/connections`.

---

## What Was Done This Session (Session 2.3a — WA codes admin CRUD)

**Done:**

- Built WA codes admin CRUD pages and wired them to the admin dashboard.
- Surfaced schema issue: `GET /wa-codes/{id}/connections` has no `response_model`, so the generated client types the response as `unknown`. The `hasConnections` check in `WaCodeFormDialog.tsx` uses a cast as a workaround. Backend fix tracked in backend HANDOFF.

**Next:** Session 2.3b (Contractors), 2.3c (Hygienists), or 2.3d (Employee Role Types) — pick any; all unblocked.

**Blockers:** Session 2.3e (Deliverables) — backend still needs `POST /deliverables/` + `PATCH /deliverables/{id}`. `WaCodeFormDialog.tsx` cast cleanup — backend needs `WaCodeConnections` response model on `GET /wa-codes/{id}/connections`.

---

## What Was Done This Session (Auth fix — 401 interceptor redirect)

**Done:**

- Diagnosed two bugs causing a stuck/broken state on `/admin/employees` when the session token expired:
  1. `queryClient` has `staleTime: 30_000`, so `ensureQueryData` in `_authenticated.tsx` `beforeLoad` returns cached `/users/me` data, allowing the route guard to pass even with an expired token.
  2. The 401 interceptor in `store.ts` called `clearAuth()` but never redirected, leaving the user on the page with a blank top bar and a failed data table.
- Updated `src/auth/store.ts`: the 401 interceptor now also calls `queryClient.removeQueries({ queryKey: currentUserQueryKey() })` (clears stale user cache) and `window.location.href = "/login"` (hard redirect); imported `queryClient` from `@/api/queryClient` and `currentUserQueryKey` from `@/auth/api`.

**Next:** Session 2.3a — WA codes admin CRUD.

**Blockers:** Session 2.3b (Deliverables admin) — backend still needs `POST /deliverables/` + `PATCH /deliverables/{id}`.

---

## What Was Done This Session (Backend pickup migration — regenerated client + role-type shape)

**Done:**

- Audited the regenerated OpenAPI client against all outstanding backend pickup items from HANDOFF.md.
- Confirmed: contractors paginated ✅, hygienists paginated ✅, `EmployeeRole` shape changed to `role_type_id + role_type: EmployeeRoleTypeRead` ✅, new `/employee-role-types/` CRUD endpoints ✅.
- Confirmed still missing: `POST /deliverables/` and `PATCH /deliverables/{id}` — Session 2.3b remains blocked.
- Migrated `EmployeeRolesTab.tsx` — `role.role_type` → `role.role_type.name` (two sites).
- Migrated `EmployeeRoleFormDialog.tsx` — schema uses `role_type_id: z.coerce.number().min(1)`, select options fetched from `listEmployeeRoleTypesOptions()`, create body passes `role_type_id`.
- Extended `src/features/employees/api/employees.ts` with five new role-type wrappers.
- Updated `EmployeeRoleFormDialog.test.tsx` — `SAMPLE_ROLE` has `role_type_id` + `role_type` object, mock includes `listEmployeeRoleTypesOptions`, 409 test adds select step.
- Updated HANDOFF.md — removed resolved pickup items, kept deliverables blocker and work-auth pagination note.

**Next:** Session 2.3a — WA codes admin CRUD.

**Blockers:** Session 2.3b (Deliverables admin) — backend still needs `POST /deliverables/` + `PATCH /deliverables/{id}`.

---

## What Was Done This Session (Planning session — Session 2.3 split + backend pickups)

**Done:**

- Audited generated client (`types.gen.ts`, `sdk.gen.ts`, `@tanstack/react-query.gen.ts`) against Session 2.3 scope; found three backend gaps: contractors + hygienists are not paginated, and deliverables have no single-item create/update.
- Split Session 2.3 into four sub-sessions (2.3a–2.3d) in ROADMAP.md; 2.3b/c/d marked blocked with notes.
- Marked Session 2.2 complete in ROADMAP.md (was `[ ]` despite HANDOFF already reporting it done).
- Added backend pickup items to "Backend changes pending frontend pickup" (paginate contractors/hygienists list; add POST/PATCH deliverables).

**Next:** Session 2.3a — WA codes admin CRUD.

**Blockers:** Sessions 2.3b/c/d await backend pagination (contractors, hygienists) and deliverables create/update endpoints.

---

## What Was Done This Session (Session 2.2 — Extract generics + retrofit)

**Done:**

- Created `src/hooks/useEntityForm.ts` — 4-generic hook encapsulating RHF setup, reset-on-open effect, create/update mutation pair, per-key cache invalidation, `applyServerErrors` → toast fallback. Hook owns `onSuccess`/`onError`; callers supply mutation options, `buildCreateVars`/`buildUpdateVars` adapters, `invalidateKeys`, and `entityLabel`.
- Created `src/components/EntityListPage.tsx` — generic `<EntityListPage<T>>` owning `useUrlSearch` + `useUrlPagination`, running the list query, rendering Card-wrapped `DataTable` with header/search/`actions` slot.
- Deleted `src/features/schools/components/SchoolsList.tsx` and `src/features/employees/components/EmployeesList.tsx`.
- Rewrote `src/pages/admin/schools/index.tsx` and `src/pages/admin/employees/index.tsx` as thin compositions over `EntityListPage`; `actions` slot supplies the Import CSV / Add Employee buttons; `useFormDialog` used for dialog state (normalized Schools and Employees).
- Rewrote `src/features/employees/components/EmployeeFormDialog.tsx` to consume `useEntityForm`; public prop signature unchanged; fields JSX unchanged.
- Created `src/components/EntityListPage.test.tsx` (6 tests: heading, rows, empty state, actions slot, onRowClick, search navigate).
- Created `src/hooks/useEntityForm.test.ts` (6 tests: isEdit flag, reset-on-open, create path, update path, 422 → field error / no toast, generic error → toast).
- Created `src/components/EntityListPage.stories.tsx` — Default, WithActions, Loading, Empty, Error.
- Appended to `src/PATTERNS.md`: Entity admin list pattern, Entity form pattern, `src/fields/` rationale, Testing strategy (closes both HANDOFF open items from Session 2.1).

**Next:** Session 2.3 — Contractors, hygienists, WA codes, deliverables.

**Blockers:** none

---

## What Was Done This Session (Session 1.5C — Storybook primitive stories + UI showcase)

**Done:**

- Created `src/components/ui/Button.stories.tsx` — all 6 variants (Default, Outline, Secondary, Ghost, Destructive, Link), disabled state, all-variants grid, all-sizes grid, with-icon story
- Created `src/components/ui/Card.stories.tsx` — Default (with footer), WithAction (CardAction slot), SmallSize
- Created `src/components/ui/Inputs.stories.tsx` — Input (default/disabled/invalid), Textarea, Select, Checkbox, FieldGroup (with FieldError), InputGroup (search, prefix/suffix, button addon)
- Created `src/components/ui/Dialog.stories.tsx` — Default (edit form), Destructive (confirm delete); both use trigger button, not forced-open
- Created `src/components/ui/Tabs.stories.tsx` — Default (pill variant), LineVariant
- Created `src/components/ui/Table.stories.tsx` — Default (rows with Badge status), Empty (colspan message)
- Created `src/components/ui/Misc.stories.tsx` — Badge all variants, Separator (horizontal + vertical), Skeleton (text lines + avatar row)
- Created `src/components/ui/Overlay.stories.tsx` — Popover (with header/description), Command (search + group + empty state)
- Created `src/stories/Showcase.stories.tsx` — composite `UI/Showcase / Admin page` story combining all primitives: top bar + sidebar + stat cards + tabs (list/loading) + dialog + form + table; `layout: "fullscreen"`
- Updated `src/PATTERNS.md` Storybook section — added note on shadcn primitive coverage + requirement to ship stories with new primitives
- `pnpm tsc --noEmit`, `pnpm check` — all clean

**Next:** Session 2.2 — Extract generics + retrofit (Schools + Employees → `EntityListPage`/`EntityFormDialog`)

**Blockers:** none

---

## What Was Done This Session (Admin shell import refactor)

**Done:**

- Deleted `src/components/admin/` — admin shell components were misplaced in the global shared layer; they are admin-section-specific, not domain-free primitives
- Created `src/pages/admin/components/` — moved all five files (`AdminShell.tsx`, `AdminSidebar.tsx`, `AdminTopBar.tsx`, `nav-items.ts`, `AdminShell.stories.tsx`); internal relative imports unchanged
- Created `src/pages/admin/layout.tsx` — exports `AdminLayout`; renders `<AdminShell><Outlet /></AdminShell>`; the only consumer of the shell components outside their own directory
- Trimmed `src/routes/_authenticated/admin.tsx` — removed inline `AdminLayout` function and direct `AdminShell` import; now a thin route file: `beforeLoad` guard + `component: AdminLayout` from `@/pages/admin/layout`
- Updated `src/pages/admin/index.tsx` — import path changed from `@/components/admin/AdminShell` to `./components/AdminShell`
- `pnpm check` — clean

**Next:** Session 1.5C — Storybook primitive stories + UI showcase

**Blockers:** none

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

**Next:** Session 1.5C — Storybook primitive stories + UI showcase

**Blockers:** none

---

## What Was Done This Session (Session 1.5B — Admin shell)

**Done:**

- Created `src/lib/admin-shell-state.ts` — Zustand store; `sidebarCollapsed` persisted to `localStorage` under `"admin-shell"`; `pageTitle`/`pageActions` in-memory only (not persisted)
- Created `src/components/admin/nav-items.ts` — discriminated-union `AdminNavItem` type; `ADMIN_NAV_ITEMS` array (Dashboard, Schools, Employees enabled; Projects/Contractors disabled)
- Created `src/components/admin/AdminSidebar.tsx` — collapsible left rail (`w-60` expanded / `w-16` icon-only); active state via `useRouterState`; disabled items render as non-interactive spans; collapse toggle button at bottom
- Created `src/components/admin/AdminTopBar.tsx` — reads `pageTitle`/`pageActions` from Zustand; right side has user chip + ThemeToggle + sign-out
- Created `src/components/admin/AdminShell.tsx` — `AdminShell` (flex row: sidebar + stacked topbar/main); `AdminShell.Title` and `AdminShell.Actions` compound slots that write to Zustand via `useEffect`, invisible null-renders; Zustand store avoids React re-render loops
- Created `src/components/admin/AdminShell.stories.tsx` — Default / Collapsed / WithSamplePage stories; memory-router decorator with `initialEntries: ["/admin"]`
- Updated `src/routes/_authenticated.tsx` — skips `AppShell` wrapper when `pathname.startsWith("/admin")`; admin routes get full-page `AdminShell` instead
- Updated `src/routes/_authenticated/admin.tsx` — mounts `<AdminShell><Outlet /></AdminShell>`
- Updated `src/components/AppShell.tsx` — removed Admin ghost-link (GearIcon → `/admin/schools`); nav lives in AdminSidebar now
- Rewrote `src/pages/admin/index.tsx` — WP-style card grid (Schools, Employees live; Projects/Contractors disabled); `AdminShell.Title` sets "Dashboard" in top bar
- `pnpm tsc --noEmit`, `pnpm test` (5/5 green), `pnpm check` — all clean

**Next:** Session 1.5C — Storybook primitive stories + UI showcase

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
