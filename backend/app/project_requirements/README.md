# `app/project_requirements`

## Purpose

Owns the `ProjectRequirement` protocol, the handler registry, and the closure-gate
aggregator. Provides a single `get_unfulfilled_requirements_for_project()` function
that walks every registered requirement type and returns a uniform
`UnfulfilledRequirement` list — replacing what would otherwise be N bespoke per-silo
walks in the project closure gate.

Does **not** own: per-silo state machines (those live in their own modules —
`app/required_docs/`, etc.); dismissal endpoints (per-silo); trigger-config CRUD
(`wa_code_requirement_triggers`, Session B); or blocking notes
(`app/notes/` stays orthogonal — requirements answer "what should be true",
notes answer "something is currently wrong").

---

## Non-obvious behavior

**Adapter pattern, not inheritance.** `DeliverableRequirementAdapter` and
`BuildingDeliverableRequirementAdapter` do not inherit `ProjectRequirement` — they
satisfy it structurally (Python `typing.Protocol`). Any class that exposes the
six protocol attributes + `is_fulfilled()` satisfies the check.

**Registration is a module import side-effect.** When `app.project_requirements` is
imported, its `__init__.py` imports the `adapters` subpackage, which imports
`adapters/deliverables.py`, which executes the `@register_requirement_type(...)` class
decorators. This registers both deliverable adapters in the global `registry` singleton.
Nothing is registered until that import chain runs — never assume the registry is
populated before `app.project_requirements` has been imported.

**`_DERIVABLE_SCA_STATUSES` lives in `app.projects.services`.** The adapter imports it
directly. This is intentional: `projects/services.py` is the authoritative owner of the
deliverable closure predicate; the adapter must mirror it exactly. If the set changes,
there is one place to edit and the adapter follows automatically.

**Mixins are defined but unused in Session A.** `DismissibleMixin` and
`ManualTerminalMixin` are declared here so silos (Sessions C–E) can inherit them. No
model inherits them yet; Session A produces no schema diff.

**`requirement_key` is opaque.** Deliverable adapter encodes `str(deliverable_id)`;
building deliverable encodes `f"{deliverable_id}:{school_id}"`. Keys are stable within
a `(requirement_type, project_id)` scope. Per-type endpoints introduced in Session F
will parse them.

---

## Before you modify

**The equivalence gate is the load-bearing invariant.** `test_aggregator.py::TestAggregatorEquivalence::test_count_matches_derive_project_status`
asserts that `len(get_unfulfilled_requirements_for_project(p)) ==
derive_project_status(p).outstanding_deliverable_count` for a mixed-status fixture.
If this breaks after a change to the adapter or aggregator, the abstraction has diverged
from the existing closure gate. **Stop and resolve before merging.**

**New requirement types must call `registry.register()` at import time.** The canonical
way is `@register_requirement_type("type_name")` on the handler class; wire the import
through `adapters/__init__.py` or the relevant silo module's `__init__.py`. Add a test
in the silo's `tests/test_aggregator.py` mirroring the deliverable equivalence pattern.

**Tests use the global registry.** Importing `app.project_requirements.aggregator`
triggers the `app.project_requirements.__init__` side effect that registers both
deliverable adapters. Tests that need a clean registry should instantiate a local
`RequirementTypeRegistry()` rather than calling `registry.clear()` on the global.
