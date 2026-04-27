# `app/common/requirements`

## Purpose

Owns the `ProjectRequirement` protocol, the handler registry, the event dispatcher,
and the closure-gate aggregator. Provides a single `get_unfulfilled_requirements_for_project()`
function that walks every registered requirement type and returns a uniform
`UnfulfilledRequirement` list — replacing what would otherwise be N bespoke per-silo
walks in the project closure gate.

Does **not** own: per-silo state machines (those live in their own modules —
`app/required_docs/`, `app/cprs/`, etc.); dismissal endpoints (per-silo); trigger-config
CRUD (`app/requirement_triggers/`); or blocking notes (`app/notes/` stays orthogonal —
requirements answer "what should be true", notes answer "something is currently wrong").

---

## Non-obvious behavior

**Adapter pattern, not inheritance.** `DeliverableRequirementAdapter` and
`BuildingDeliverableRequirementAdapter` do not inherit `ProjectRequirement` — they
satisfy it structurally (Python `typing.Protocol`). Any class that exposes the
six protocol attributes + `is_fulfilled()` satisfies the check.

**Registration is a module import side-effect.** Silo modules register their handlers
via `@register_requirement_type(...)` in their `service.py` (or `requirement_adapter.py`
for deliverables). Those files are imported at startup via each module's `__init__.py`
side-effect import. Nothing is registered until those import chains run — never assume
the registry is populated before the app has been imported.

**`_DERIVABLE_SCA_STATUSES` lives in `app.projects.services`.** The deliverable adapter
imports it directly. This is intentional: `projects/services.py` is the authoritative
owner of the deliverable closure predicate; the adapter must mirror it exactly.

**Mixins are defined in `protocol.py`.** `DismissibleMixin` and `ManualTerminalMixin`
are declared here so silos can inherit them. No contract-layer code uses them at runtime;
they are compile-time annotations for the silo models.

---

## Before you modify

**The equivalence gate is the load-bearing invariant.** `tests/test_aggregator.py::TestAggregatorEquivalence::test_count_matches_derive_project_status`
asserts that `len(get_unfulfilled_requirements_for_project(p)) ==
derive_project_status(p).outstanding_deliverable_count`. If this breaks, the adapter
pattern has diverged from the existing closure gate. **Stop and resolve before merging.**

**New requirement types must call `registry.register()` at import time.** The canonical
way is `@register_requirement_type("type_name")` on the handler class; wire the import
through the relevant silo module's `__init__.py`. Add a test mirroring the deliverable
equivalence pattern.

**Tests use the global registry.** Tests that need isolation should instantiate a local
`RequirementTypeRegistry()` rather than calling `registry.clear()` on the global.
