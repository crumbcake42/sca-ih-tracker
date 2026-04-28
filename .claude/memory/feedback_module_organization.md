---
name: Domain-based module organization with strict hierarchy
description: Where shared/contract primitives live vs domain-specific config; cross-module import direction; URL-namespace ownership rules
type: feedback
originSessionId: eb605ecb-687e-48bc-8a94-c208788565d3
---
Shared/contract primitives belong under `app/common/<topic>/` (e.g.
`app/common/requirements/` for protocol/registry/aggregator/dispatcher).
Domain-specific config and routes belong in their own named module whose
**name matches what the module owns** (e.g. `app/requirement_triggers/`
owns the `WACodeRequirementTrigger` model and `/requirement-triggers`
route — not `app/project_requirements/`, which is broader than the
contents).

Cross-module imports must reflect a strict hierarchy: the contract layer
imports nothing from concrete implementations; implementations import
only from the contract layer plus their own dependencies. Read-only
adapters (e.g. `DeliverableRequirementAdapter`) live with the domain
they wrap, not in the contract layer.

URL hierarchy is owned by the parent: child modules export sub-routers
with no parent prefix; parent modules mount them. Child modules never
declare the parent's URL prefix from inside their own router file.

When a new requirement-style abstraction lands, factor the same way from
day one: contract → implementations, never co-located.

**Why:** Conflating contract with one specific config (the
`project_requirements/` mix during Phase 6.5 Sessions A–D) makes
downstream modules import primitives from a path that suggests
"everything related lives here," obscuring the hierarchy and making
later splits expensive (every silo imported from the wrong path).
Letting children declare the parent's URL prefix puts URL-namespace
ownership in the wrong place and accumulates as more children are
added.

**How to apply:** Before adding a new module, ask whether its contents
are (a) a contract that other modules will implement (→ `app/common/`),
(b) a specific data model + its routes (→ named after what it owns), or
(c) a wrapper around an existing domain (→ inside that domain's module).
If the answer is mixed, split before writing the second file. For
routers, ask whether the URL hierarchy you are about to declare belongs
to this module or to a parent — if parent, export a no-prefix sub-router
and let the parent mount it (mirrors `app/wa_codes/router/__init__.py`
mounting `requirement_triggers_router`).
