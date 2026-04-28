# `app/requirement_types`

## Purpose

Owns the `GET /requirement-types` metadata endpoint. Returns one `RequirementTypeInfo`
row per handler registered in `app/common/requirements/registry.py` — name, subscribed
events, JSON Schema for accepted `template_params`, dismissability, and optional display
name.

Does **not** own: requirement handler registration (each silo's `service.py` or
`requirement_adapter.py` does that); the `ProjectRequirement` protocol or registry
singleton (those live in `app/common/requirements/`); per-silo CRUD or state machines.

---

## Non-obvious behavior

**Reads the live registry at request time.** The registry is populated via side-effect
imports in `app/main.py`. If a handler is not imported before the app starts, it won't
appear in the response. The startup import chain in `main.py` is the guarantee.

**`template_params_schema` is derived from `handler.template_params_model`.** Handlers
that accept no params declare `template_params_model = None`; the endpoint emits `{}`
for those. Only `ProjectDocumentHandler` (`project_document`) declares a real Pydantic
model today. Future handlers: set `template_params_model: ClassVar[type[BaseModel] | None]`
on the handler class.

**`display_name` defaults to `None`.** No handler currently declares one. Future handlers
can set `display_name: ClassVar[str]` and the endpoint picks it up via `getattr`.

---

## Before you modify

- Adding a new requirement type: register it in its silo's `service.py` with
  `@register_requirement_type(...)` and ensure `main.py` imports the module at startup.
  Also add the new name to `RequirementTypeName` in `app/common/requirements/__init__.py`
  — the Literal-vs-registry coverage test (`test_registry_coverage.py`) will catch drift.
- Adding a field to `RequirementTypeInfo`: check whether the source data is on the handler
  class (use `getattr`) or on the registry (add a helper to `RequirementTypeRegistry`).
  Do not reach into `registry._handlers` or `registry._events` directly from the router —
  use the public helpers (`items()`, `events_for()`).
