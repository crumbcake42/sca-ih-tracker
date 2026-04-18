Give me a pickup briefing for this project. I may have worked on it from another machine since my last session here, so the local `~/.claude/` memory may be stale — treat committed docs and git as source of truth.

Do these in parallel:

1. Read `frontend/HANDOFF.md` and `backend/HANDOFF.md`.
2. Run `git log --oneline -20` and `git status`.
3. Read the memory index for this session's root folder, and skim the project-type memories it links to.

Then report, tight and scannable, in this order:

- **Where we are** — one line per side (frontend / backend) pulled from HANDOFF current-state.
- **Recent activity** — bullets for commits in the last ~2 weeks, grouped by side if obvious.
- **Next step** — what HANDOFF says to do next (per side).
- **Stale memory** — list any project-type memory whose claim is contradicted by HANDOFF or recent commits. Format: `- <file>: <what looks stale>`. Say "none" if nothing looks off.
- **Local state** — anything in `git status` worth noting. Otherwise omit.

Keep the whole thing under ~25 lines. Do not edit files, do not start work — this is a read-only briefing.

After the briefing, as me if I want to update the local memory to fill in the gaps found.