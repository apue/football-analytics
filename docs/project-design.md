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
- `.codex/hooks.json` registers the Stop hook;
  `.codex/hooks/course_turn_stop.py` detects a dirty worktree and hands the
  semantic decision to `.codex/skills/course-turn-checkpoint/`.
- `src/football_analytics/` contains reusable analysis utilities.
- Notebooks orchestrate lesson analysis and narrative; reusable definitions do
  not live only in notebooks.
- External and processed data remain untracked.

## Resume Contract

A new session reads course state, the active lesson brief and handoff, then
inspects `git status`, recent commits, and any diff. It reports the latest
recoverable commit, post-commit work, and one next action before continuing.
There is no parser or parallel course-state runtime: the tracked text and Git
history are the interface.

## Checkpoint Contract

At turn end, Codex first checks whether the worktree is dirty. When it is,
the repository Skill uses task context and the actual diff to decide
independently whether the change is ready to commit, whether a focused check
is needed, and whether learning progress changed.

Meaningful, coherent lesson units update the handoff and use local commits
named:

```text
checkpoint(<lesson-id>): CP-NNN <step>
```

Technical work that does not advance learning uses a normal commit and leaves
the handoff alone. Unfinished work stays uncommitted. Lesson branches are not
pushed until review.

The Stop hook performs only `git status --porcelain`. It runs no tests, makes
no semantic decision, edits no file, and creates no commit.

## Dependency Policy

- Runtime dependencies must be used by current repository code.
- Notebook and analysis packages live in opt-in dependency groups.
- Modeling packages are added only when an active lesson needs them.
- Core lessons run on local CPU.

## Validation

The course has no generic validator because lesson progress and football
interpretation do not have one universal expected output. Checks are selected
from the current change and analytical risk:

- prose and course-state edits normally receive diff review;
- deterministic reusable code receives focused tests;
- notebook sections are checked while built and the complete lesson notebook
  runs from a clean kernel at review;
- push and PR delivery run the relevant branch-wide checks and CI.

Previously successful checks are not repeated against unchanged content solely
to create a checkpoint.

## Delivery

Each completed lesson is delivered through one pull request. CI must pass and
the learner must explicitly confirm before squash merge.
