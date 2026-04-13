# Schema — Lab Results

Two-layer design: admin-configurable sample type definitions (config layer) and per-job recorded batches (data layer). Adding a new sample type requires no code or migration — an admin adds rows to the config tables.

---

## Config Layer

```mermaid
erDiagram
    sample_types {
        int id PK
        string name
        text description
        bool allows_multiple_inspectors
    }

    sample_subtypes {
        int id PK
        int sample_type_id FK
        string name
    }

    sample_unit_types {
        int id PK
        int sample_type_id FK
        string name
    }

    turnaround_options {
        int id PK
        int sample_type_id FK
        int hours
        string label
    }

    sample_type_required_roles {
        int id PK
        int sample_type_id FK
        enum role_type
    }

    sample_type_wa_codes {
        int sample_type_id PK "FK → sample_types"
        int wa_code_id PK "FK → wa_codes"
    }

    wa_codes {
        int id PK
        string code
        string description
    }

    sample_types ||--o{ sample_subtypes : "has subtypes"
    sample_types ||--o{ sample_unit_types : "counted in"
    sample_types ||--o{ turnaround_options : "available turnarounds"
    sample_types ||--o{ sample_type_required_roles : "requires role"
    sample_types ||--o{ sample_type_wa_codes : "billed under"
    wa_codes ||--o{ sample_type_wa_codes : "covers"
```

---

## Data Layer

```mermaid
erDiagram
    sample_batches {
        int id PK
        int sample_type_id FK
        int sample_subtype_id FK
        int turnaround_option_id FK
        int time_entry_id FK
        string batch_num
        bool is_report
        date date_collected
        text notes
        enum status
        datetime created_at
    }

    sample_batch_units {
        int id PK
        int batch_id FK
        int sample_unit_type_id FK
        int quantity
        decimal unit_rate
    }

    sample_batch_inspectors {
        int batch_id PK "FK → sample_batches"
        int employee_id PK "FK → employees"
    }

    time_entries {
        int id PK
        datetime start_datetime
        datetime end_datetime
        int employee_id FK
        int project_id FK
        int school_id
    }

    sample_types {
        int id PK
        string name
    }

    sample_subtypes {
        int id PK
        int sample_type_id FK
        string name
    }

    turnaround_options {
        int id PK
        int sample_type_id FK
        string label
        int hours
    }

    sample_unit_types {
        int id PK
        int sample_type_id FK
        string name
    }

    employees {
        int id PK
        string first_name
        string last_name
    }

    time_entries ||--o{ sample_batches : "collected during"
    sample_types ||--o{ sample_batches : "typed as"
    sample_subtypes ||--o| sample_batches : "subtyped as"
    turnaround_options ||--o| sample_batches : "turnaround"

    sample_batches ||--o{ sample_batch_units : "contains"
    sample_unit_types ||--o{ sample_batch_units : "unit type"

    sample_batches ||--o{ sample_batch_inspectors : "collected by"
    employees ||--o{ sample_batch_inspectors : "inspector on"
```

---

## Notes

**`sample_batches.is_report`** — distinguishes two documents:
- `false` (default): the handwritten COC received from the field
- `true`: the printed lab report document (table of results) received from the lab; required for project closure

**`sample_batches.status`** (Phase 4 — migration pending):
| Value | Meaning |
|-------|---------|
| `active` | Normal state |
| `orphaned` | `time_entry_id` was deleted or revised past `date_collected`; `time_entry_id` becomes NULL; blocks project closure until re-linked or discarded |
| `discarded` | Explicitly invalidated by a manager |
| `locked` | Project closed; read-only |

**`sample_batch_units.unit_rate`** is nullable — it will be populated from a future `sample_rates` config table (billing follow-up project). Until then, quantities are tracked without a rate value.

**Unit type scoping** — `sample_batch_units.sample_unit_type_id` must belong to the batch's `sample_type_id`. The app layer validates this on insert (422 otherwise).

**`sample_type_required_roles`** — which `EmployeeRoleType` values an employee must hold to collect this sample. If a sample type has no required roles, any employee with an active role on `date_collected` is accepted.

**Quick-add endpoint** (`POST /lab-results/batches/quick-add`, Phase 4 remaining): accepts `project_id`, `school_id`, `employee_id`, `date_collected` instead of `time_entry_id`. Creates a system placeholder time entry if none exists for that employee/project/school/date.
