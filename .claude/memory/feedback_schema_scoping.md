---
name: Only add columns that drive logic
description: User prefers schemas pruned to fields that actually affect application behavior (closure gates, validations, status derivation) — don't add tracking columns "just because the real-world flow has that step"
type: feedback
originSessionId: a90755f4-bab9-48f6-a220-2f16cba4af16
---
When modeling real-world workflows, only include columns for stages/fields that the application actually acts on. If a downstream step exists in the real world but has no bearing on app logic (closure gates, validations, derived status), leave it out — it's dead weight.

**Why:** Real-world processes often have more stages than the system needs to track. Example from CPR (contractor payment record) plan: SCA does a final RFP review after we save the document, but once we've saved, the project can close regardless of their ultimate decision. Including `rfp_sca_status` / `rfp_sca_resolved_at` would be dead columns. User explicitly called this out during planning.

**How to apply:** When designing schema for a multi-stage workflow, ask for each column: "what application behavior depends on this?" If the answer is "nothing — it's just the real-world next step," drop it. If someone later needs to track it, it can be added as a dedicated note, a future column with a clear purpose, or not at all. Prefer fewer columns over completeness-for-its-own-sake.
