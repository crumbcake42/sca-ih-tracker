# Schema — Deliverable Tracking

Deliverable definitions, their WA code triggers, and per-project/per-building status tracking.

```mermaid
erDiagram
    deliverables {
        int id PK
        string name
        text description
        enum level
    }

    wa_codes {
        int id PK
        string code
        enum level
    }

    deliverable_wa_code_triggers {
        int deliverable_id PK "FK → deliverables"
        int wa_code_id PK "FK → wa_codes"
    }

    projects {
        int id PK
        string project_number
    }

    project_school_links {
        int project_id PK "FK → projects"
        int school_id PK "FK → schools"
    }

    project_deliverables {
        int project_id PK "FK → projects"
        int deliverable_id PK "FK → deliverables"
        enum internal_status
        enum sca_status
        text notes
        datetime added_at
    }

    project_building_deliverables {
        int project_id PK "FK → projects"
        int deliverable_id PK "FK → deliverables"
        int school_id PK "composite FK → project_school_links"
        enum internal_status
        enum sca_status
        text notes
        datetime added_at
    }

    deliverables ||--o{ deliverable_wa_code_triggers : "triggered by"
    wa_codes ||--o{ deliverable_wa_code_triggers : "triggers"

    projects ||--o{ project_deliverables : "tracks"
    deliverables ||--o{ project_deliverables : "tracked on"

    projects ||--o{ project_building_deliverables : "tracks"
    deliverables ||--o{ project_building_deliverables : "tracked on"
    project_school_links ||--o{ project_building_deliverables : "scoped to building"
```

## Notes

**`deliverables.level`** controls which table rows land in:
- `project` → one `project_deliverables` row per project
- `building` → one `project_building_deliverables` row per linked school on the project

**`deliverable_wa_code_triggers`** is static config (seeded, rarely changed). It defines which WA codes, when added to a work auth, should cause `ensure_deliverables_exist()` to create the corresponding deliverable row if it doesn't already exist. This is implemented in Phase 5.

**Two-status tracking** — each row carries two independent statuses:

`internal_status` (tracks internal preparation):
| Value | Meaning |
|-------|---------|
| `incomplete` | Not started |
| `blocked` | Blocked — `notes` must explain why |
| `in_review` | Internal review in progress |
| `in_revision` | Returned for revision |
| `completed` | Internally complete |

`sca_status` (tracks SCA-facing submission lifecycle):
| Value | Derivable? | Meaning |
|-------|-----------|---------|
| `pending_wa` | ✓ auto | No work auth exists yet |
| `pending_rfa` | ✓ auto | WA exists but required code is pending RFA |
| `outstanding` | ✓ auto | Code is active; deliverable not yet submitted |
| `under_review` | manual | Submitted to SCA |
| `rejected` | manual | Rejected by SCA |
| `approved` | manual | Approved by SCA |

The first three `sca_status` values are maintained by `recalculate_deliverable_sca_status(project_id)` (Phase 5). The last three are set manually.
