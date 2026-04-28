Finalize a unit of work: propose commits, reconcile cross-side HANDOFFs, then commit only after explicit OK.

## Steps

1. Read the diff:
   - `git status`
   - `git diff --stat`
   - `git log --oneline @{upstream}..HEAD` (commits ahead of remote, if any)

2. Identify which side(s) the diff covers (`frontend/` only, `backend/` only, or both).

3. Verify HANDOFF coverage:
   - For each touched side, check that its `HANDOFF.md` has a recent dated "What Was Done" entry that describes this work.
   - If missing, prompt the user to run `/note` first (or do it inline if the user OKs).
   - For cross-side work, ensure each HANDOFF includes a one-line cross-reference pointing at the other.

4. Propose commit boundaries:
   - **Default**: one commit per session, message format `Phase X.Y Session Z: <topic>` (matches existing repo history).
   - **Split**: if the diff genuinely spans logical units (e.g. unrelated cleanup + feature + tests), propose 2–3 commits with separate messages, and state which files go into which.

5. Draft each commit message:

   ```
   Phase X.Y Session Z: <one-line summary>

   <wrapped paragraph or bullet list mirroring the HANDOFF "What Was Done" block>
   ```

   - Use HEREDOC for multi-line messages.
   - Sub-bullets indented with two spaces, not tabs.
   - No trailing period on the subject line.

6. Show the user the full plan: branch, commit count, full text of each message, exact file lists per commit.

## Confirmation gates

Wait for explicit "OK" or "go" in the same turn before any of:

- `git add <specific files>` — never `git add -A` or `git add .`.
- `git commit -m "$(cat <<'EOF' … EOF)"` — one per proposed boundary.

After commits land, output:

```
git log --oneline -5
```

so the user can verify the new history.

## Hard rules

- Never `git push`, `git push --force`, or `git push -u` during `/wrap` unless the user explicitly says "push it."
- Never amend a previous commit unless the user explicitly says "amend."
- Never `--no-verify` or skip hooks.
- If a pre-commit hook fails, stop and surface the error — do not retry with `--no-verify`. Fix the underlying issue, re-stage, create a new commit.
