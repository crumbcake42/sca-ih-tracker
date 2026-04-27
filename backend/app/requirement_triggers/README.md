# `app/requirement_triggers`

## Purpose

Owns the `WACodeRequirementTrigger` ORM model and the `/requirement-triggers` admin
CRUD router. Triggers are admin-managed rows that instruct the dispatcher to materialize
a given requirement type whenever a WA code is added to a project.

Does **not** own: the `ProjectRequirement` protocol, registry, dispatcher, or aggregator
(those live in `app/common/requirements/`); per-silo state machines; or the deliverable
adapter.

---

## Non-obvious behavior

**`hash_template_params` enforces deduplication.** The unique constraint on
`wa_code_requirement_triggers` covers `(wa_code_id, requirement_type_name,
template_params_hash)`. Key order in the JSON dict does not matter — the hash is
canonical. `POST /requirement-triggers` computes the hash before inserting and returns
409 if a matching trigger already exists.

**`requirement_type_name` is validated against the live registry.** `POST
/requirement-triggers` calls `registry.get(name)` and returns 422 for unknown types.
The registry must be populated (via startup side-effect imports) before this endpoint
is reachable — guaranteed by `app/main.py`'s top-of-file import chain.

**Router is mounted at two paths.** `app/main.py` includes the router at
`/requirement-triggers` (global admin list). `app/wa_codes/router/__init__.py` mounts it
as a nested sub-router under `/wa-codes`, yielding `/wa-codes/requirement-triggers`.
Both paths are intentional; do not remove either mount without verifying frontend usage.
