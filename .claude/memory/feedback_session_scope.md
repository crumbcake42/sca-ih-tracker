---
name: Keep session context scoped to the active side
description: Only read files under the root folder Claude was invoked in; if in-scope docs aren't enough, ask the user for permission to cross — never attempt a cross-side read first
type: feedback
originSessionId: 98678828-401f-444e-bdc8-6fe629170162
---
During a backend session, do not read frontend HANDOFF.md, frontend ROADMAP.md, or any other frontend doc to plan the work. The root folder Claude is called in is the hard boundary.

The same applies in reverse: during a frontend session, don't read backend source files (models, routers, schemas, etc.).

**Why:** Sessions are intentionally scoped to one side to keep context tight and avoid scope creep from the other side's state. This rule has been corrected multiple times — treat "I'll just peek at the other side" as a violation, not a shortcut.

**How to apply:**
- For backend data shapes in a frontend session, check `src/api/generated/types.gen.ts` only.
- If a generated type is `any` or `unknown`, flag it to the user rather than reading backend source to find the real type.
- The only exception is at the end of a session when changes need to be communicated to the other side — write a note to the other side's HANDOFF.md.
- **If the in-scope HANDOFF/docs don't contain enough context to proceed:** stop, tell the user what's unclear, and ask for explicit permission to read outside the current root. Do not attempt the cross-side read and rely on the user denying the tool call to catch it.
