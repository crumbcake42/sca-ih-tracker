Append a lean "What Was Done" entry to the active side's `HANDOFF.md`. Touch nothing else.

## Steps

1. Run `git diff --stat HEAD` and `git status -s` to see what changed in this session.
2. Decide which HANDOFF(s) to update:
   - Diff under `frontend/` → update `frontend/HANDOFF.md`
   - Diff under `backend/` → update `backend/HANDOFF.md`
   - Both → update both, with a one-line cross-reference in each
3. Look at any commits made this session via `git log <session-start-ref>..HEAD --oneline` if a starting ref is known; otherwise summarize from the diff alone.
4. Append one dated entry to the relevant HANDOFF, just above any existing dated entries (newest-first ordering matches the existing HANDOFF style). Format:

   ```markdown
   ## YYYY-MM-DD — <one-line summary>

   - <bullet, past tense>
   - <bullet, past tense>
   - <bullet, past tense>

   <optional 1-line cross-side note: "Backend pickup: …" or "Frontend pickup: …">
   ```

5. Output the appended block to the user so they can confirm it landed.

## Hard limits

- **Do not** update `PATTERNS.md`, `ROADMAP.md`, `module/README.md`, or any memory files. Those are `/gnight`'s territory (cross-machine) or a deliberate `/wrap` follow-up.
- **Do not** rewrite or reorganize prior entries. Append-only.
- If no diff and no new commits exist, output `No changes this session — nothing to log.` and stop.
- Keep the entry to ~10 lines max. Bullets, not prose.
