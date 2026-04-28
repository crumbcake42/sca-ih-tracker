**Use only when switching computers.** For routine session start, `/brief` is enough — this command is heavier and includes `~/.claude/` memory-sync verification.

Give me a pickup briefing for this project. I may have worked on it from another machine since my last session here, so the local `~/.claude/` memory may be stale — treat committed docs and git as source of truth.

Do these in parallel:

1. Read `frontend/HANDOFF.md` and `backend/HANDOFF.md`.
2. Run `git log --oneline -20` and `git status`.
3. Read the memory index for this session's root folder, and skim the project-type memories it links to.
4. **Memory drift check** — diff the in-repo `.claude/memory/` snapshot against the live user memory at `~/.claude/projects/<project-key>/memory/` (whichever the system memory directory resolves to on this machine). Note any files present in one but not the other, or files whose content differs.

Then report, tight and scannable, in this order:

- **Where we are** — one line per side (frontend / backend) pulled from HANDOFF current-state.
- **Recent activity** — bullets for commits in the last ~2 weeks, grouped by side if obvious.
- **Next step** — what HANDOFF says to do next (per side).
- **Memory drift** — list any project-type memory whose claim is contradicted by HANDOFF/recent commits, OR any file present in `.claude/memory/` but missing from `~/.claude/...` (or vice versa). Format: `- <file>: <what's stale or differs>`. Say "none" if nothing looks off.
- **Local state** — anything in `git status` worth noting. Otherwise omit.

Keep the whole thing under ~25 lines. Do not edit files, do not start work — this is a read-only briefing.

After the briefing, ask whether to:

- Refresh `~/.claude/projects/<key>/memory/` from the in-repo `.claude/memory/` snapshot (if drift was detected and the in-repo copy is newer).
- Or, if memory looks current, hand off to `/brief` for a leaner per-session view going forward.
