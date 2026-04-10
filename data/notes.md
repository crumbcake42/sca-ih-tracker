Implement Phase 1 remaining modules; fix db-setup; update Phase 2 design

Phase 1 — new modules
- hygienists: full CRUD (GET/POST/PATCH/DELETE /hygienists/)
- wa_codes: read + search + batch CSV import; WACodeLevel enum (project/building)
- deliverables: read + search + batch CSV import
- employee_roles: full CRUD nested under /employees/{id}/roles with date-overlap
  validation; EmployeeRoleType enum (Air Monitor, Air Technician, Project Monitor,
  Lead Risk Assessor)
- employees: added GET /employees/ and GET /employees/{id} read endpoints
- Migration c9e1f3d72a08 creates all four new tables
- db.py seed hooks added for hygienists.csv, wa_codes.csv, deliverables.csv

Bug fixes — db-setup script
- Role configuration: re-fetch newly created Role with selectinload before assigning
  permissions, preventing greenlet error from lazy="joined" collection access
- User/Role queries: add .unique() before .scalars() to handle duplicate rows
  produced by lazy="joined" on Role.permissions

Phase 2 design — roadmap updated
- work_auths schema: wa_num, service_id, project_num (all unique strings),
  initiation_date, project_id FK
- work_auth_wa_codes: updated to 5-value status enum (rfa_needed, rfa_pending,
  active, added_by_rfa, removed); RFA timestamps moved off this table
- rfas table: status (pending/approved/rejected/withdrawn), submitted_at,
  resolved_at (nullable); one-pending-per-work-auth enforced at app layer;
  no resolved_by_id (resolver is always SCA)
- rfa_wa_codes: rfa_id, wa_code_id, action (add/remove), project_school_link_id
  (nullable FK for building-level codes)
- Design note added: building-level codes use project_school_link_id rather than
  plain school_id to enforce school belongs to the project