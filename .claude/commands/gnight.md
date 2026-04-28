**Use only before leaving a machine.** For routine session end, `/note` is enough — this command is the heavier flow that *also* persists `~/.claude/` memory into the in-repo `.claude/memory/` snapshot so memory state travels with the next push.

## Steps

1. Determine which side(s) this session touched (`git diff --stat HEAD` and recent commits).

2. For each touched side, update its `HANDOFF.md`:
   - Reflect current state, what was done, what's next, any non-obvious decisions made.
   - For cross-side work, add a one-line cross-reference in each HANDOFF pointing at the other.

3. Update `ROADMAP.md` only if a permanent design decision was made or the phase plan changed.

4. Update the relevant `PATTERNS.md`:
   - Backend: `backend/app/PATTERNS.md` — only if a new cross-cutting SQLAlchemy/FastAPI pattern was established.
   - Frontend: `frontend/src/PATTERNS.md` — only if a new component/query/form convention was established.

5. Update `app/{module}/README.md` (backend) only if module behavior changed in a non-obvious way.

6. **Memory sync (cross-machine)**: copy current `~/.claude/projects/<project-key>/memory/*.md` into the in-repo `.claude/memory/` directory so the snapshot travels with the next push.
   - The user-level memory directory resolves from your system context (the path the auto-memory system reports).
   - Use `cp` (or platform equivalent) to copy each `.md` file. Skip files that are byte-identical.
   - After copying, output a list of which files changed (added / updated / deleted from the snapshot) so the user can see what the next commit will include.

Keep each documentation update focused — only change what's actually different from what's already written. If `/note` already wrote today's "What Was Done" block, don't duplicate it; just verify ROADMAP / PATTERNS / READMEs are consistent.
