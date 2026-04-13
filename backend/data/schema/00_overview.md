# Database Schema — Domain Overview

High-level map of the six domains and how data flows between them. See the numbered files in this directory for ER diagrams with full column details.

---

```mermaid
graph TD
    subgraph AUTH["Auth & Access"]
        users
        roles
        permissions
    end

    subgraph REF["Reference Data"]
        schools
        contractors
        hygienists
        wa_codes
        deliverables
        employees
    end

    subgraph PROJ["Projects"]
        projects
        project_school_links
        project_manager_assignments
        project_contractor_links
        project_hygienist_links
    end

    subgraph WA["Work Authorizations"]
        work_auths
        work_auth_project_codes
        work_auth_building_codes
        rfas
        rfa_project_codes
        rfa_building_codes
    end

    subgraph DELIV["Deliverable Tracking"]
        deliverable_wa_code_triggers
        project_deliverables
        project_building_deliverables
    end

    subgraph FIELD["Field Activity"]
        employee_roles
        time_entries
    end

    subgraph LAB["Lab Results"]
        sample_types
        sample_batches
        sample_batch_units
        sample_batch_inspectors
    end

    AUTH -->|"controls write access"| PROJ
    AUTH -->|"controls write access"| WA
    AUTH -->|"controls write access"| FIELD
    AUTH -->|"controls write access"| LAB

    REF -->|"schools, contractors, hygienists\nlinked to"| PROJ
    REF -->|"wa_codes placed on"| WA
    REF -->|"deliverables tracked via"| DELIV
    REF -->|"employees hold roles for"| FIELD

    PROJ -->|"one work auth per project"| WA
    PROJ -->|"deliverables scoped to"| DELIV
    PROJ -->|"time entries scoped to\nproject + school"| FIELD

    WA -->|"code additions trigger\ndeliverable requirements"| DELIV
    FIELD -->|"sample batches linked to"| LAB
```

---

## Domain Summaries

| Domain | Purpose | Key Tables |
|--------|---------|------------|
| **Auth** | User authentication and role-based permissions | `users`, `roles`, `permissions` |
| **Reference Data** | Seed/config entities that don't change often | `schools`, `wa_codes`, `employees`, `deliverables` |
| **Projects** | Core project record with linked people and buildings | `projects`, `project_school_links` |
| **Work Authorizations** | WA issuance, code tracking, and RFA approval flow | `work_auths`, `rfas` |
| **Deliverable Tracking** | Two-status lifecycle per deliverable per project/school | `project_deliverables`, `project_building_deliverables` |
| **Field Activity** | Time entries recording employee work on a project + school | `employee_roles`, `time_entries` |
| **Lab Results** | Sample batches collected in the field, linked to time entries | `sample_types`, `sample_batches` |
