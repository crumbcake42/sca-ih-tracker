# Schema — Projects

The core project record and all entities linked to it: buildings (schools), contractors, hygienists, and manager assignment history.

```mermaid
erDiagram
    projects {
        int id PK
        string name
        string project_number
    }

    schools {
        int id PK
        string code
        string name
        string address
        enum city
        string state
        string zip_code
    }

    project_school_links {
        int project_id PK "FK → projects"
        int school_id PK "FK → schools"
    }

    contractors {
        int id PK
        string name
        string address
        string city
        string state
        string zip_code
    }

    project_contractor_links {
        int project_id PK "FK → projects"
        int contractor_id PK "FK → contractors"
        bool is_current
        datetime assigned_at
    }

    hygienists {
        int id PK
        string first_name
        string last_name
        string email
        string phone
    }

    project_hygienist_links {
        int project_id PK "FK → projects"
        int hygienist_id FK
        datetime assigned_at
    }

    project_manager_assignments {
        int id PK
        int project_id FK
        int user_id FK
        int assigned_by_id FK
        datetime assigned_at
        datetime unassigned_at
    }

    users {
        int id PK
        string username
    }

    projects ||--o{ project_school_links : "takes place at"
    schools ||--o{ project_school_links : "hosts"

    projects ||--o{ project_contractor_links : "assigned"
    contractors ||--o{ project_contractor_links : "works on"

    projects ||--o| project_hygienist_links : "assigned"
    hygienists ||--o{ project_hygienist_links : "works on"

    projects ||--o{ project_manager_assignments : "managed by"
    users ||--o{ project_manager_assignments : "manages"
```

## Notes

- `project_school_links` is also used as a **composite FK target** by `work_auth_building_codes`, `rfa_building_codes`, `project_building_deliverables`, and `time_entries`. Any row in those tables is guaranteed to reference a `(project_id, school_id)` pair that exists here.
- `project_contractor_links.is_current` flags the active contractor. A project can have historical contractor entries; only one should have `is_current = true` at a time.
- `project_hygienist_links` is effectively one-to-one (project_id is the PK), modelled as a link table so assignment history can be added later without a schema change.
- `project_manager_assignments` is an **append-only audit trail**. The active manager is the row where `unassigned_at IS NULL`. Reassignment closes the current row and inserts a new one — rows are never updated in-place.
- `projects` and `schools` carry `AuditMixin` columns — omitted above for clarity.
