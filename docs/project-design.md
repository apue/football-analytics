# Project Design

## Purpose

This repository is a question-led football analytics course. The learner owns
the football question, assumptions, interpretation, and final claims. Code and
automation exist only to make lesson work reproducible, reviewable, and easy to
resume.

## Boundaries

- `course/state.yaml` points to the sole active lesson and records completed
  lessons.
- The active lesson's `handoff.md` is the only resumable course snapshot.
- Git checkpoint commits are the recovery history; no parallel journal, agent
  memory, or evaluation tree is maintained.
- `src/football_analytics/` contains reusable analysis or course utilities.
- Notebooks orchestrate lesson analysis and narrative; reusable definitions do
  not live only in notebooks.
- External and processed data remain untracked.

## Resume Contract

`scripts/course_resume.py` is read-only. It reports:

- active lesson, status, current step, and next action;
- current branch and clean or dirty worktree state;
- the latest checkpoint for the active lesson that is reachable from `HEAD`;
- warnings for a missing checkpoint, an unexpected branch, or uncommitted work.

Resume does not validate lesson templates, execute notebooks, model status
transitions, inspect other branches, or modify Git state. Only unreadable or
invalid state and handoff metadata are fatal.

## Checkpoint Contract

Meaningful lesson units use local commits named:

```text
checkpoint(<lesson-id>): CP-NNN <step>
```

Before a checkpoint, update the handoff, run checks proportional to that unit,
and inspect the diff. Lesson branches are not pushed until review. Git history
is the checkpoint history; the handoff stores only the latest snapshot.

## Dependency Policy

- Runtime dependencies must be used by current repository code.
- Notebook and analysis packages live in opt-in dependency groups.
- Modeling packages are added only when an active lesson needs them.
- Core lessons run on local CPU.

## Validation

Default repository validation is:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python scripts/validate_course.py
uv run python scripts/validate_notebook.py course/templates/analysis.ipynb
```

Resume behavior is covered by focused CLI and Git-state tests. Actual lesson
notebooks are executed from a clean kernel at review, not at every checkpoint.

## Delivery

Each completed lesson is delivered through one pull request. CI must pass and
the learner must explicitly confirm before squash merge.
