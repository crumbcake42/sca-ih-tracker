# Generic `project_requirement` Pattern — Design Evaluation

## Context

You're asking whether the menagerie of closure-gating concepts already in the
system (deliverables, planned document requirements, planned contractor
payment records, planned DEP filings, the lab-results sample-type-WA-code
gap) could be unified under a single `project_requirement` abstraction with
a small inheritance hierarchy:

```
project_requirement                  — boolean: fulfilled / not
  required_document                  — fulfilled when "saved on file" toggled
  deliverable                        — composes ≥1 required_documents,
                                       adds external SCA progress track,
                                       fulfilled when SCA-approved
  contractor_payment_record          — single required_document with
                                       internal-only RFA/RFP date tracking
                                       (tracking does not gate the saved
                                       flag, but defines its own logic)
```

Plus an admin-managed config layer where WA codes (and possibly templates,
projects) declare which requirement instances must materialize — analogous
to `sample_type_wa_codes`, `sample_subtypes`, `sample_unit_types`.

The reference doc's §7 (predicted/actual seams), §7.4 (two-track status
recurrence), and §8 points 2/3/7 (refactor pressure) all gesture in this
direction without naming it. This document evaluates the idea from a
purely logical standpoint.

### Constraints that shape the recommendation

You confirmed three framing constraints in conversation that materially
narrow the design space:

1. **Adoption curve will grow then flatten.** New requirement types are
   expected during the adoption period as more managers self-track work
   they currently can't see, with eventual settling once the steady-state
   set is discovered. The abstraction's leverage is therefore highest
   *during the next 12–24 months*, lower thereafter — argues for putting
   the primitive in place before that growth happens, not after.
2. **Notes module stays orthogonal.** Requirements answer "what should be
   true on this project"; notes answer "something is currently wrong."
   Both feed the closure aggregator independently. Phase 6.5's existing
   silo plans already imply this split — keep it.
3. **Motivation is composite.** Phase 6.5 is about to ship three new
   silos (timing pressure), admin-self-serve flexibility is on the
   medium-term roadmap (long-term pressure), and the schema's recurring
   shape suggests latent abstraction debt (general pressure). All three
   point toward the same intervention: introduce the primitive *before*
   Phase 6.5 ships, not after.

---

## 1. Where the abstraction maps cleanly

### 1.1 Closure gating collapses to one query

Today's closure gate (§6.4) walks four sources of blocking notes plus
checks `is_locked`. Phase 6.5 (§6.5) adds three more silos with three
custom WHERE clauses (`not_satisfied AND not_dismissed`,
`rfp_saved_at IS NULL`, `is_saved=False`). All of those collapse into:

```
SELECT 1 FROM project_requirements
WHERE project_id = :p
  AND NOT is_fulfilled
  AND NOT is_dismissed
```

That's the strongest argument for the abstraction. Every Phase 6.5 silo,
every two-track status track, every "saved on file?" flag becomes one
boolean roll-up. Closure-gate logic stops being a list of bespoke walks
and becomes one predicate.

### 1.2 The two-track status pattern (§7.4) is not coincidence

Deliverables already carry `(internal_status, sca_status)` with manual-
terminal immunity. Phase 6.5's CPR carries paired RFA-internal/RFA-SCA
plus RFP-internal/RFP-SCA. Both fit a generic shape:

```
requirement.is_fulfilled          ← derived from internal_state ⊕ external_state
requirement.internal_state        ← can be auto-derived
requirement.external_state        ← manual terminals immune to recalc
```

The user's framing ("deliverable adds an additional status track on top
of the document being saved") names this directly. The abstraction earns
its keep here: instead of every silo re-deriving manual-terminal
immunity, it's a property of the requirement type.

### 1.3 WA-code → trigger config is already the right shape

`deliverable_wa_code_triggers` exists today. Phase 6.5 plans
`wa_code_expected_entities`. Both are "WA code X causes thing Y to be
required on this project." Generalizing to `wa_code → requirement_type`
triggers (where requirement_type is polymorphic — deliverable_template,
document_type, CPR-template, etc.) means one config table replaces two
planned ones, and the LAMP18 example becomes a normal config row:

```
wa_code = LAMP18
requirement_template = "Contractor Payment Review" deliverable
which composes → required_document of type CPR
                 (the same CPR primitive that contractor-link
                  auto-materialization uses)
```

### 1.4 The "system-notes as history substitute" pattern (§7.3) co-locates

Stage regressions on requirements (RFA approved → later rejected;
deliverable approved → revised) want a per-requirement audit trail.
Today this is fragmented; in a generic model, each requirement carries
its own notes (already polymorphic, already auto-resolving). The notes
module — already the most generic mechanism in the system (§8 point 2)
— just gains one more `entity_type`.

### 1.5 Phase 6.5's hardest unresolved question becomes a per-type method

§5.7 and §8 point 7 flag placeholder→actual matching as the largest
unsolved design question. In a requirement registry, each type defines
its own `try_match(actual_entity) -> bool`. The match-promote-or-dismiss
primitive (§8 point 7) becomes a method on the requirement type, not a
new layer to design from scratch.

### 1.6 Templates fall out for free

`project_templates` (speculative, §1.1) becomes "a named bundle of
requirements + WA-code triggers." Project setup = pick a template =
materialize the requirements. No new entity needed beyond the template
itself.

---

## 2. Where the abstraction strains

### 2.1 The lab-results analogy is partial

Lab-results config validates *data the user enters* (a batch's subtype
must belong to its sample type). The user's proposed requirement config
*materializes rows* (WA code triggers requirement creation). Both are
config+data, but the data flow is different: validate-on-write vs.
materialize-on-trigger. The doc's §7 already names this — the
requirements abstraction is firmly a "predicted/actual seam," not a
data-validation seam.

Practical consequence: requirement materialization needs idempotent
"ensure" semantics (like `ensure_deliverables_exist` today) plus
de-materialization rules (what happens when the triggering WA code is
removed by an RFA?). Lab-results config has no analog for the latter.
This is a real piece of plumbing that doesn't come for free from the
analogy.

### 2.2 Lab batches are not requirements; sample-type-WA-code gaps already are

Worth separating in the design conversation. A `SampleBatch` is
operational data — its closure gate is `status != active`. The
predicted/actual seam in lab-results is the `sample_type_wa_codes` gap
(Cycle C), and that's already enforced via a blocking system note. So
"requirements" generalizes from deliverables and Phase 6.5 silos; it
does *not* swallow lab batches. The gap-note mechanism either stays as
a notes-based blocker (orthogonal) or is reworded as a requirement
("WA must contain code X if any batch of type T exists"), but the batch
itself is not a requirement.

### 2.3 Polymorphism cost is real and load-bearing

Notes today are the only polymorphic table (`entity_type`, no FK; §3, §4
Cycle J). That works because notes are advisory — a dangling note is
recoverable. Requirements would be on the closure-gating critical path:
a dangling row blocks `is_fulfilled` forever. Three SQLAlchemy
realizations, each with a real downside:

- **Single Table Inheritance.** Sparse columns; hard to add NOT NULL
  invariants per type; queryable. CLAUDE.md doesn't forbid STI.
- **Joined Table Inheritance.** CLAUDE.md forbids JTI for lab results
  config types — that ban was scoped to admin-managed type definitions,
  not data rows, so it does not literally bind here. But the underlying
  reasons (selectin-load complexity, awkward queries, N+1 risk; PATTERNS
  rule 4) still apply.
- **Concrete inheritance + read-layer view.** Each type keeps its own
  table; an aggregator (view or service function) presents the unified
  interface. Cheapest path. Loses the "FK directly to a polymorphic
  parent" but you don't actually need that for closure walks.

### 2.4 Composition (deliverable = N required_documents) compounds the polymorphism

Open questions the abstraction must answer:

- Are required_documents always inside a deliverable, or can they stand
  alone? (You implied both: minor letter, re-occupancy letter standalone;
  CPR inside "Contractor Payment Review.")
- Can one required_document satisfy multiple deliverables? (Probably no
  — but must be explicit.)
- Is a required_document inside a deliverable separately addressable in
  the closure list, or only via its parent? (Reasonable answer: it's
  fulfilled-by-parent — you only see the deliverable in closure UI, the
  document is internal detail.)
- Does "fulfilled" propagate up automatically (a deliverable's
  `is_fulfilled = all(child_documents.is_fulfilled) AND sca_approved`)?

These are answerable, but every answer adds rules the framework must
encode and tests must cover.

### 2.5 Per-requirement business rules stubbornly do not generalize

The Phase 6.5 closure gates (§6.5) all collapse to "fulfilled?", but the
*derivations* are bespoke:

- Document: `is_saved=True` (one boolean).
- CPR: `rfp_saved_at IS NOT NULL` (single timestamp; SCA's post-save
  review intentionally NOT tracked — a *deliberate* asymmetry with
  deliverables).
- DEP filing: `is_saved=False`.
- Deliverable: `sca_status = approved`.

The abstraction must accept "every requirement type has its own
`compute_is_fulfilled` handler." That's the same pattern config+data
uses for sample types, so it's not a new idea — but it means the
abstraction is closer to "a registry of requirement-type plugin
classes" than "a uniform schema." The schema is uniform on the
identity/closure axis only.

### 2.6 Notes vs. requirements — not the same axis

The notes module already generalizes "things that block closure"
(blocking notes, polymorphic, dedup'd, auto-resolving). The proposed
requirements module generalizes "things that must exist on a project."
These are orthogonal:

- A *required* thing that is *missing* is one notes-emitting condition.
- A *required* thing that is *present but problematic* (overlap, sample-
  type-WA-code gap) is another notes-emitting condition.
- Notes are the *expression* of "something is wrong"; requirements are
  the *registry* of "what should be true."

A clean design says: requirements determine what must be present and
fulfilled; when a requirement is unfulfilled, the closure aggregator
uses that directly (no note needed). Notes remain for issues that don't
fit the requirement model (cross-entry overlap, ad-hoc user-authored
blockers, history of stage regressions). Trying to fold one into the
other erases a distinction that's currently working.

### 2.7 Recalc fan-out grows

§7.2 lists today's reconciliation triggers — every WA mutation, every
RFA resolve, every TimeEntry create, every SampleBatch create runs the
deliverable recalc pair. Generalized: every requirement type registers
which trigger events invalidate it. Either:

- All types recalc on all triggers (fan-out N×M; expensive at scale).
- A trigger graph defines which event invalidates which type (real
  infrastructure to build and to test).

Today's pattern (one explicit pair-call per endpoint) is crude but
auditable. A trigger graph is cleaner but adds a layer that did not
exist before.

### 2.8 Schema readability decreases for the 90% case

Today, reading `project_deliverables.py` tells you what a deliverable
is. After: reading `project_requirements.py` tells you almost nothing
without traversing the type registry, the WA-code triggers, and the
per-type handlers. CLAUDE.md's "Design Decisions (Permanent — Do Not
Re-Add)" section shows the team historically prunes columns whose
existence is theoretical. A `project_requirements` table whose rows are
90% deliverables, 5% required_documents, 5% CPRs would be a complexity
tax for projects whose requirement set is static and small.

This is the strongest argument for *not* doing the full abstraction. The
question is whether the flexibility payoff is large enough to justify
the schema-readability cost.

---

## 3. Long-term: helps admin or hinders admin?

### 3.1 Helps when (admin flexibility wins)

- New project type / new contract category arrives that requires a new
  document type (e.g., "asbestos clearance certificate"). Today: ADR +
  migration + new table + new endpoints + new closure check + new admin
  form. After: admin adds a `requirement_type` row + maps it to a WA
  code + adds a one-method handler class (or, if uniform enough, just
  config rows).
- WA code definitions evolve (LAMP18 starts requiring an extra document
  next year). Today: code-level deliverable trigger change. After:
  config row edit.
- Project templates / presets become first-class. "Asbestos abatement
  oversight" template = bundle of requirements; admin authors templates
  in UI.

If the team's medium-term direction includes (a) frequent introduction
of new document/deliverable types, (b) admin-self-serve project lifecycle
configuration, (c) per-customer or per-contract template variations, the
abstraction earns its keep.

### 3.2 Hinders when (the 90% case is uniform)

- If the requirement set is essentially static and changes with normal
  release cadence (i.e., adding a deliverable is rare and a developer
  task), the registry adds layers without removing work.
- Type-specific UI still proliferates — generic "list requirements on
  project" works, but editing a CPR's RFA dates needs a CPR-specific
  form. So both layers (generic + specific) coexist regardless. The
  generic admin UI is an addition, not a replacement.
- Debugging is harder: "why does this project have requirement X?"
  becomes a registry-traversal question instead of a code-grep.

### 3.3 The honest split

The closure-gate consolidation (§1.1 above) is a clean win — small
refactor, large readability and correctness gain in one well-bounded
area (project closure logic). The full requirement-registry abstraction
is a much bigger bet that pays off only if the team genuinely wants
admin-self-serve lifecycle configuration. Those are separable.

---

## 4. Recommendation: staged, with Stage 1 + Stage 2 done concurrently

The Phase 6.5 timing window changes the staging calculus. The original
"introduce the primitive after silos exist" sequencing is suboptimal:
once Phase 6.5 ships three more bespoke tables, you've doubled the
migration cost. Instead, introduce the primitive *as part of* the
Phase 6.5 design — the new silos are then the first native implementors,
the read-layer aggregator is trivial because there are no legacy silos
to UNION over (deliverables aside), and the abstraction is validated
against real Phase 6.5 use cases before it has to support anything else.

### Stage 1 — Define the requirement primitive (concurrent with Phase 6.5 design)

Define `ProjectRequirement` as a Python protocol/ABC with a small
contract:

- `is_fulfilled: bool` (computed per type)
- `is_dismissed: bool` plus dismissal metadata
- `compute_is_fulfilled(self, project_state) -> bool` — per-type override
- `try_match(self, candidate_actual_entity) -> bool` — the §8 point 7
  match-promote-or-dismiss primitive, finally given a home
- AuditMixin (every business entity carries it; §1.2)
- Optional two-track status mixin for types that need manual terminals
  (deliverables, CPR) — not required for plain document requirements

A separate `RequirementType` registry (developer-defined, not admin
config) maps type names to their handler classes. WA-code triggers
remain admin-managed config — `wa_code_requirement_triggers` —
generalizing today's `deliverable_wa_code_triggers` and Phase 6.5's
planned `wa_code_expected_entities`.

No polymorphic parent table. Each requirement type stays in its own
table; the protocol is enforced at the Python layer. This keeps schema
readability and avoids the JTI/STI tradeoff — if growth flattens as
you expect, you'll never need to consolidate.

### Stage 2 — Phase 6.5 silos implement the primitive natively

`project_document_requirements`, `contract_payment_records`,
`project_dep_filings` each ship as concrete tables that satisfy the
`ProjectRequirement` protocol. The closure-gate aggregator walks the
registry and asks each implementor for unfulfilled rows. Phase 6.5
closure gates (§6.5) collapse into one closure-gate function instead
of three.

This is the timing-critical step. Designing these three tables to
share a common protocol is essentially free *now*; retrofitting them
later means three migrations and three rewrites. Even if the broader
abstraction never extends further, this stage already pays for itself
in Phase 6.5 closure-gate consolidation.

### Stage 3 — Deliverables migrate only when growth confirms the bet

`project_deliverables` and `project_building_deliverables` keep their
existing tables and existing closure-gate path through Stage 2. They
join the requirement aggregator via a thin adapter (a class that
implements the protocol by reading from the existing tables). This
gives one unified closure query without touching deliverable schema.

If your adoption-curve prediction holds and new requirement types
genuinely proliferate during the next 12–24 months, deliverables can
migrate into the framework natively at that point — by then, the
abstraction has been validated against 4+ use cases, the building-
scoping pattern (composite FK to `project_school_links`) and the
template-id quirk (§4 Cycle J cross-project bleed) are well-understood,
and the migration carries real evidence.

If growth flattens early instead — the steady-state set turns out to
be small — deliverables stay where they are, the read-layer adapter
remains the only consolidation, and you've still gained the
unified-closure-gate win at zero schema-migration cost.

### Stage 4 (speculative) — Admin-self-serve config

If managers do start asking for new requirement types frequently, then
move from "developer adds a new handler class" to "admin configures
new requirement types via UI." This is the largest commitment and
should only be evaluated after Stages 1–3 have established the actual
shape of demand. Likely candidates: a generic "saved-on-file document"
type that admins can clone with new names; per-customer template
variations.

Don't design for this yet. Stage 1's developer-registered handlers
preserve the option without committing to it.

### What this avoids

- Building Phase 6.5's three silos as one-off tables that immediately
  need to be retrofitted — the most costly version of the bet.
- A speculative meta-framework that exceeds current evidence (no
  polymorphic parent table, no admin-self-serve config layer until
  demand justifies it).
- Re-doing CLAUDE.md's "lab_results NO joined-table inheritance"
  decision under a new name.
- Schema churn on the existing deliverable tables before the
  abstraction is validated.

### What this preserves

- The notes module's role for *blocking issues* (orthogonal to
  *required things*) — your stated preference.
- The config+data meta-model spirit (admin manages WA-code triggers;
  developers manage requirement types).
- §8 point 5's observation that `users.employee_id` is the higher-
  leverage missing piece — the abstraction does not need to wait on
  that, but it also does not solve the auth-relationship problem.
- Optionality: if growth flattens as you expect, Stage 4 never
  happens and the system pays no additional complexity tax beyond
  the protocol layer itself.

---

## 5. Specific answers to the questions you asked

> Could a structure like this be designed for the backend database
> similarly to how the sample results are managed with their own config
> tables?

Yes, with one caveat: the lab-results config validates data on insert,
while the requirements config materializes rows from triggers. Both are
"config + data" in spirit, but the requirements pattern needs idempotent
ensure-and-de-materialize plumbing that lab-results does not. The
admin-self-serve UX (add a row, no migration) is preserved.

> Would a pattern like this help admin define project dependencies and
> lifecycles more flexibly and include new deliverables/files/
> requirements as needed, or does it actually hinder admin by
> introducing complexity that obscures the most common use cases?

Both — and which one wins depends on adoption rate of new requirement
types. If the team adds a new document/deliverable/filing type more
often than once or twice a year, the abstraction repays itself. If
it's a once-every-few-years event, the registry is overhead for the
common case. The Stage 1 read-layer abstraction wins regardless. The
full registry only wins if there's medium-term demand for admin-self-
serve project lifecycle configuration.

> How does LAMP18 → "Contractor Payment Review" deliverable → CPR fit?

Cleanly. The abstraction supports it as a single config row:
`wa_code=LAMP18 → requirement_template="Contractor Payment Review"
deliverable, which composes one required_document of type CPR`. The
CPR primitive is the same one auto-created at contractor-link time
(per Phase 6.5 plan). Two consumers of the same primitive, one inside
a deliverable, one standalone. That's a sign the primitive is the
right granularity.

---

## 6. Open design questions worth resolving before building anything

1. **Does the abstraction subsume the notes blocking-issue module, or
   stay strictly orthogonal?** Recommend orthogonal. Notes = "something
   is wrong"; requirements = "what should be true." Conflating them
   re-creates the §9 drift problem.

2. **Are `required_documents` inside deliverables separately addressable,
   or only via their parent?** Recommend "fulfilled by parent" — the
   document is internal detail of the deliverable, not a separate row
   in the closure list.

3. **Does dismissibility live on the requirement, or on a wrapper?**
   Phase 6.5 already plans `(dismissal_reason, dismissed_by_id,
   dismissed_at)` per silo. Lift those into the requirement base.

4. **Where does the manual-terminal immunity rule live — in the base
   class or per-type?** Recommend per-type; not all requirements have
   manual terminals (a saved-flag document does not).

5. **Does the requirement table itself carry AuditMixin?** Yes. Every
   business entity does (§1.2). Manual mutations to dismissal state
   need creator/updater for audit.

6. **De-materialization on WA code removal — what happens?** If WA code
   is removed by an approved RFA, the requirements it triggered must
   either auto-dismiss (with system reason) or persist if already
   partially fulfilled. This is a real policy question; the existing
   `recalculate_deliverable_sca_status` skip-manual-terminals rule
   suggests "persist if advanced past initial state, otherwise auto-
   remove." Either choice has corner cases.

7. **Trigger graph or fan-out-everything?** Recommend explicit per-type
   trigger registration in code (not config) — admin-managed triggers
   are over-flexibility; developer-defined triggers preserve
   reviewability.

---

## 7. Verification (how this would be tested if built)

Not applicable yet — this is an evaluation, not an implementation.
If Stage 1 (read-layer abstraction) is pursued, verification would be:

- Existing closure-gate tests continue to pass (the aggregator must
  produce the same blocking-issue list as today's per-silo walks).
- A new test covers the unified query against fixtures that combine
  multiple silos into one project.
- No schema migration; no migration test.

Stage 2 verification waits on Phase 6.5 implementation specifics.
Stage 3 verification is a substantial schema-migration test surface
and is out of scope until the prior stages have shipped.

---

## End

Bottom line: the pattern is directionally aligned with the doc's stated
refactor opportunities (§8 points 2, 3, 7) and the §7.4 two-track
recurrence. The timing leverage is real and short-lived: Phase 6.5 is
the cheapest moment to introduce the primitive because the three new
silos can be born native to the protocol instead of retrofitted.
Stages 1–2 are the high-leverage commitment; Stage 3 (deliverables)
and Stage 4 (admin-self-serve) are deferred until your adoption-curve
prediction has hard evidence.

If you decide to pursue this, the first concrete step is *not* a
schema change — it's reopening the Phase 6.5 design with the question:
"can these three tables share a `ProjectRequirement` protocol?" If yes,
Stage 2 happens as part of normal Phase 6.5 implementation and Stage 1
is its precondition. If no (the silos turn out to be too divergent),
that's evidence the abstraction is wrong and the work stops there
before any commitment is made.
