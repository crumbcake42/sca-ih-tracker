Quick session pickup — keep it under 5 lines. Read-only.

Run these in parallel:

1. `git branch --show-current`
2. `git status -s` (count dirty lines)
3. `git log -1 --format='%h %s'`
4. Detect role from `pwd`:
   - At repo root → coordinator
   - Inside `frontend/` → frontend dev
   - Inside `backend/` → backend dev
5. Read just the most recent dated entry header (the first `## YYYY-MM-DD …` heading) from the active side's `HANDOFF.md`. If coordinator, read the most recent header from each of `frontend/HANDOFF.md` and `backend/HANDOFF.md`.

Then output exactly this shape (5 lines max):

```
Role: <coordinator|frontend dev|backend dev>
Branch: <name> (<N> dirty)
Last commit: <hash> <subject>
Last HANDOFF (FE): <one-line header>     # only if coordinator or fe-dev
Last HANDOFF (BE): <one-line header>     # only if coordinator or be-dev
```

That's it. **Do not** run `git log -20`, do not check memory drift, do not read full HANDOFF entries — that's `/gmorning`'s job (reserved for cross-machine pickup). If the user wants more detail after this brief, they'll ask.

Do not edit any files. Do not start work.
