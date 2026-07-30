# ACCEPTANCE

Status: accepted

## Done Definition

- [x] Git repository exists with a public GitHub remote and an initial push.
- [x] `uv sync --all-groups` succeeds from the locked project.
- [x] Hudl open data is present as an ignored shallow partial clone and has a
      documented update command.
- [x] README, AGENTS, syllabus, methodology, data guide, agent workflow, course
      state, and all lesson templates exist.
- [x] The initial stage and first lesson are detailed enough to begin in a new
      session.
- [x] Package tests and lint pass.
- [x] The template notebook is valid and executes from a clean kernel.
- [x] Git status contains no accidentally tracked external or generated data.
- [x] `course/state.yaml` uses schema v2 and contains navigation only.
- [x] The active handoff has valid frontmatter, a latest snapshot, and matching
      checkpoint history.
- [x] `scripts/course_resume.py` reports lesson, status, checkpoint, branch,
      next action, checkpoint-commit consistency, and worktree state without
      modifying the repository.
- [x] Validator and resume tests cover all specified status and recovery cases.

## Acceptance Scenarios

1. Given a new coding-agent session, when it follows `AGENTS.md`, then it can
   identify the current lesson, status, next action, and required validation
   without chat history.
2. Given a clean repository clone, when the documented bootstrap commands run,
   then dependencies and public data can be restored.
3. Given an analytical claim, when lesson findings are written, then its
   evidence level and limitations are explicit.
4. Given a core lesson, when it runs on supported open event data, then it does
   not require GPU or paid cloud compute.
5. Given a new session on a clean checkpoint, when the resume command runs,
   then it identifies the durable checkpoint and concrete next action.
6. Given changes after a checkpoint, when the resume command runs, then it
   labels them as uncommitted post-checkpoint work and does not alter them.
7. Given inconsistent state, handoff, or Git history, when validation or resume
   runs, then it exits non-zero with actionable diagnostics.

## Manual Review Checklist

- [x] Behavior matches SPEC.
- [x] Architecture boundaries are preserved.
- [x] Reuse and cleanup report was considered.
- [x] Public-repository hygiene was inspected.
- [x] Validation plan passed or remaining delta is recorded.

## Out of Scope

- A completed football analysis or trained model.
- Automated cloud deployment.
- Private notes or proprietary data handling.
