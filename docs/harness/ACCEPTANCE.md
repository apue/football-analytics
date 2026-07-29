# ACCEPTANCE

Status: accepted

## Done Definition

- [ ] Git repository exists with a public GitHub remote and an initial push.
- [ ] `uv sync --all-groups` succeeds from the locked project.
- [ ] Hudl open data is present as an ignored shallow partial clone and has a
      documented update command.
- [ ] README, AGENTS, syllabus, methodology, data guide, agent workflow, course
      state, and all lesson templates exist.
- [ ] The initial stage and first lesson are detailed enough to begin in a new
      session.
- [ ] Package tests and lint pass.
- [ ] The template notebook is valid and executes from a clean kernel.
- [ ] Git status contains no accidentally tracked external or generated data.

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

## Manual Review Checklist

- [ ] Behavior matches SPEC.
- [ ] Architecture boundaries are preserved.
- [ ] Reuse and cleanup report was considered.
- [ ] Public-repository hygiene was inspected.
- [ ] Validation plan passed or remaining delta is recorded.

## Out of Scope

- A completed football analysis or trained model.
- Automated cloud deployment.
- Private notes or proprietary data handling.
