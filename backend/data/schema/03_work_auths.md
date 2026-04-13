# Schema — Work Authorizations

Work auth issuance, WA code placement, and the RFA approval workflow for adding/removing codes after issuance.

```mermaid
erDiagram
    wa_codes {
        int id PK
        string code
        string description
        enum level
        decimal default_fee
    }

    work_auths {
        int id PK
        string wa_num
        string service_id
        string project_num
        date initiation_date
        bool is_saved
        int project_id FK
    }

    work_auth_project_codes {
        int work_auth_id PK "FK → work_auths"
        int wa_code_id PK "FK → wa_codes"
        decimal fee
        enum status
        datetime added_at
    }

    work_auth_building_codes {
        int work_auth_id PK "FK → work_auths"
        int wa_code_id PK "FK → wa_codes"
        int project_id PK "composite FK → project_school_links"
        int school_id PK "composite FK → project_school_links"
        decimal budget
        enum status
        datetime added_at
    }

    project_school_links {
        int project_id PK "FK → projects"
        int school_id PK "FK → schools"
    }

    rfas {
        int id PK
        int work_auth_id FK
        enum status
        datetime submitted_at
        datetime resolved_at
        int submitted_by_id FK
        text notes
    }

    rfa_project_codes {
        int rfa_id PK "FK → rfas"
        int wa_code_id PK "FK → wa_codes"
        enum action
    }

    rfa_building_codes {
        int rfa_id PK "FK → rfas"
        int wa_code_id PK "FK → wa_codes"
        int project_id PK "composite FK → project_school_links"
        int school_id PK "composite FK → project_school_links"
        enum action
        decimal budget_adjustment
    }

    projects {
        int id PK
        string project_number
    }

    users {
        int id PK
        string username
    }

    projects ||--o| work_auths : "one WA per project"

    work_auths ||--o{ work_auth_project_codes : "project-level codes"
    wa_codes ||--o{ work_auth_project_codes : "placed on WA"

    work_auths ||--o{ work_auth_building_codes : "building-level codes"
    wa_codes ||--o{ work_auth_building_codes : "placed on WA"
    project_school_links ||--o{ work_auth_building_codes : "scoped to building"

    work_auths ||--o{ rfas : "change requests"
    users ||--o{ rfas : "submitted by"

    rfas ||--o{ rfa_project_codes : "project-level changes"
    wa_codes ||--o{ rfa_project_codes : "code in question"

    rfas ||--o{ rfa_building_codes : "building-level changes"
    wa_codes ||--o{ rfa_building_codes : "code in question"
    project_school_links ||--o{ rfa_building_codes : "scoped to building"
```

## Notes

**WA code status enum** (`wa_code_status`):
| Value | Meaning |
|-------|---------|
| `rfa_needed` | Code required but no active RFA covers it |
| `rfa_pending` | Code is in a currently submitted RFA |
| `active` | On the WA at issuance — no RFA involved |
| `added_by_rfa` | Added via an approved RFA |
| `removed` | Was on the WA, now removed |

**RFA status enum** (`rfa_status`): `pending` → `approved` / `rejected` / `withdrawn`

**RFA action enum** (`rfa_action`): `add` or `remove`

**Project vs building split:**
- `wa_codes.level = "project"` → goes in `work_auth_project_codes`
- `wa_codes.level = "building"` → goes in `work_auth_building_codes` (scoped to a specific school on the project)
- The app layer enforces this; inserting a building-level code into the project table returns 422.

**RFA resolve logic:**
- `approved` → sets matching `work_auth_*_codes.status` to `added_by_rfa` or `removed`; applies `budget_adjustment` to `work_auth_building_codes.budget`
- `rejected` / `withdrawn` → reverts affected codes to `rfa_needed`

**One pending RFA per work auth** is enforced at the application layer.

- `work_auths` and `rfas` carry `AuditMixin` columns — omitted above for clarity.
