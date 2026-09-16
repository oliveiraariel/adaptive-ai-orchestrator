# Incident — Safe fast-forward with untracked cache and historical stash

**Date:** 2026-09-16  
**Context:** SGFP Stage 11 / Adaptive Bridge synchronization

## What happened

The local `ariel-agent-skills` checkout needed to fast-forward to the Bridge
version containing the governed pre-admission retry fix.

The update was initially blocked because the checkout contained:

- `adaptive-orchestrator-bridge/scripts/__pycache__/`;
- `adaptive-orchestrator-bridge/tests/__pycache__/`;
- a preexisting historical stash.

No evidence had yet shown tracked or staged WIP.

The preservation policy was correct—do not discard unknown state—but the
classification was too coarse. "Repository is not literally clean" was treated
as equivalent to "fast-forward would endanger WIP."

## Correct interpretation

Repository state must be separated into:

1. tracked unstaged modifications;
2. staged modifications;
3. untracked files;
4. stash entries.

A historical stash is independent from the current checkout and may remain
untouched during a fast-forward.

Generated untracked Python caches do not by themselves make a fast-forward
unsafe. They can remain on disk while tracked files advance, unless Git reports
a path collision that would overwrite an untracked file.

## Governed decision procedure

Before synchronization:

```bash
git branch --show-current
git status --porcelain=v1 --untracked-files=all
git diff --name-only
git diff --cached --name-only
git stash list
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
```

A preservation-safe fast-forward is allowed when:

- tracked diff is empty;
- staged diff is empty;
- untracked files are known generated artifacts or otherwise do not collide with
  paths the update needs to write;
- the historical stash is left untouched;
- synchronization can use `git pull --ff-only`.

After synchronization, re-check:

```bash
git rev-parse HEAD
git status --porcelain=v1 --untracked-files=all
git stash list
```

This proves that:

- the intended HEAD was reached;
- generated untracked files were preserved;
- the stash remained intact;
- no tracked WIP was lost.

## Stop conditions

Stop instead of updating when:

- `git diff --name-only` is non-empty;
- `git diff --cached --name-only` is non-empty;
- Git warns that an untracked file would be overwritten;
- the update is not a fast-forward;
- preservation cannot be demonstrated.

## Prohibited shortcuts

Do not use these merely to make the checkout look clean:

```text
git reset --hard
git clean
git stash pop
git stash apply
git stash drop
rm -rf __pycache__
```

The goal is not cosmetic cleanliness. The goal is **preservation-safe
synchronization**.

## Reusable lesson

```text
non-empty working tree
does not automatically mean
unsafe fast-forward
```

The correct question is whether tracked/staged WIP or a real untracked-path
collision would be overwritten.

This lesson is promoted to the repository-governed strategy catalog as:

```text
classify-git-state-before-safe-fast-forward
```
