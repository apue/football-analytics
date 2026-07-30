---
name: course-turn-checkpoint
description: Review repository changes at the end of a Codex turn and decide whether they need a focused check, a lesson handoff update, and a local commit. Use after a turn modifies this football-analytics repository, when a Stop hook reports a dirty worktree, when the learner asks to pause or checkpoint work, or before pushing a lesson branch.
---

# Course Turn Checkpoint

Treat Git as the recovery mechanism and `handoff.md` as the latest learning
snapshot. Do not turn checkpoints into a generic validation framework.

## Close a turn

1. Run `git status --short`.
2. If the worktree is clean, stop. Do not update the handoff or create an empty
   commit.
3. Inspect `git diff --stat`, `git diff`, and staged changes. Separate
   task-owned changes from pre-existing learner work.
4. Make two independent decisions:
   - **Commit readiness:** Is the current change coherent, intentional, and
     recoverable? Is one focused check needed to make that judgment?
   - **Learning progress:** Did the learner complete or materially advance a
     learning unit, make a course decision, pause, or become blocked?
5. Act on the matching case:

| Commit ready | Learning progressed | Action |
| --- | --- | --- |
| no | no | Leave the diff untouched and explain the unfinished boundary. |
| no | yes | Update `handoff.md` to describe progress and unfinished work, but do not commit. |
| yes | no | Run only any check needed for this change and create a normal local commit. Do not edit `handoff.md`. |
| yes | yes | Update `handoff.md`, run only any check needed for this unit, and create a local checkpoint commit. |

Use reasoning from the current task and diff. File presence, line count, or a
passing generic test suite cannot decide whether learning progressed.

## Choose checks

Do not run tests merely because the worktree is dirty. Run the smallest check
that resolves a real uncertainty introduced by the diff:

- pure prose or course-state edits usually need diff review only;
- reusable deterministic code should get a focused test or direct exercise;
- notebook analysis should be checked while building it, then executed from a
  clean kernel when it enters review;
- a failed or unrun relevant check must be recorded when pausing or handing off.

Do not rerun a check that already ran against the same unchanged content unless
fresh evidence is needed.

## Update the handoff

Update only the active lesson's `handoff.md`, and only when learning progress
changed. Keep it as a concise latest snapshot:

- advance `checkpoint_id` only when creating a checkpoint;
- state completed work, current boundary, decisions, relevant checks or known
  gaps, open questions, and one concrete `next_action`;
- set `status` to `paused` or `blocked` when appropriate;
- update `course/state.yaml` only when global course navigation changes.

Technical cleanup, CI configuration, and documentation maintenance do not by
themselves represent learning progress.

## Commit

Before committing, inspect the final diff and stage only task-owned paths.
Preserve unrelated changes.

- For a learning checkpoint, use
  `checkpoint(<lesson-id>): CP-NNN <step>`.
- For a coherent non-learning change, use a normal conventional commit.
- Never push merely because a turn ended.
- If the change is not ready, leave it uncommitted and say why.

## Resume and deliver

At session start, read `course/state.yaml`, the active `brief.md` and
`handoff.md`, then inspect `git status`, `git log --oneline -5`, and any diff.
Summarize the latest recoverable commit, post-commit work, and next action
before continuing.

On an explicit push or PR request, inspect the complete branch diff, choose the
relevant full checks, repair failures in a bounded loop, then push. Do not merge
without explicit learner confirmation.
