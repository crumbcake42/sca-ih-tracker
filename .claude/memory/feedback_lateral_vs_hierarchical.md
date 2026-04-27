---
name: Lateral peer clusters vs hierarchical ownership
description: How to handle lateral peer navigation (singular vs many-to-many) vs hierarchical ownership; the two-layer rule that replaced the peer-route factory plan
type: feedback
originSessionId: eb605ecb-687e-48bc-8a94-c208788565d3
---
Some entity groups in this app are **hierarchical**: a parent owns
children via FK, cascade governs orphaning, and the URL nests as
`/parent/{id}/child/{id}`. Examples: `sample_type → sample_subtype`,
`project → project_deliverable`, `work_auth → work_auth_project_code`.
These use the existing patterns: FK + cascade, guarded-delete factory
for top-level entities, ordinary REST URL nesting.

Other entity groups are **lateral peer clusters**: peers exist
independently, related by domain rules, no peer owns the others, and
any peer can be the entry point for navigating to its peers. Example:
field-work cluster — `lab_result ↔ time_entry ↔ daily_log ↔
wa_code_assignment`.

**The two-layer rule for lateral peers** (replaces the earlier
peer-route factory plan, dropped in the 2026-04-27 architecture
evaluation):

1. **Singular peers** (parent has at most one related peer, usually
   via an FK column on the parent itself) → embed the peer in the
   parent's Read schema via `selectin` eager-load. No new endpoint.
   The FE renders hyperlinks from the embedded IDs / labels in one
   round-trip. Example: `SampleBatchRead.time_entry: TimeEntryMini |
   None`.
2. **Genuine many-to-many lateral peers** (parent has zero-to-many
   peers, found via composite key match or join) → one bespoke
   endpoint per edge with a **descriptive name** (not a generic
   `<peer>` pluralization). Example: `GET
   /lab-results/{batch_id}/matching-daily-logs`. Shape it to consumer
   need (filters + pagination where cardinality warrants).

Constraints either way: project scoping enforced inside the query
(look up parent, extract `project_id`, filter peers); each lateral
endpoint returns the **project-scoped form** of the peer
(`WorkAuthProjectCode`, not `WACode`); query lives in the parent's
module; reciprocal model imports are read-only and not circular.

Materialization (creating missing peers when one is added) stays
event-driven through `dispatch_requirement_event` regardless of which
read pattern is used.

**Why:** the peer-route factory was designed against a 4×3=12
endpoint estimate, but most of those collapse to singular FK
navigation (Layer 1, no endpoint at all). The genuine many-to-many
lateral edges in the field-work cluster turn out to be 3–4 — below
the threshold where a factory pays off. Hand-rolled endpoints with
descriptive names also encode the actual semantics in the URL
(`matching-daily-logs` says more than `daily-logs`) and accept
filters/pagination naturally. Reasoning detail in
`backend/PLANNING-peer-navigation.md`.

**How to apply:** Before wiring a new cross-module read endpoint, ask
in order:
1. Does the parent *own* the peer (single direction, cascade on
   delete)? → FK + nested URL.
2. Is the relationship singular (FK on parent → at most one peer)? →
   add a relationship on the model with `lazy="selectin"` and embed
   the peer in the Read schema. No endpoint.
3. Is it genuinely many-to-many lateral? → one bespoke endpoint with
   a descriptive name on the parent's item router; shape to consumer
   need.

**Factory extraction trigger** (deferred, not currently planned):
revisit the peer-route factory only if 8+ lateral edges with
genuinely uniform shape land. The frozen design constraints above
carry forward; extraction at that point is a refactor, not a
redesign.
