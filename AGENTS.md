# Agent Working Agreement

This repository is a learning system, not a notebook dump. The learner owns the
football question, assumptions, interpretation, and final claims. The agent
owns implementation quality, reproducibility, validation, and clear
explanation.

## Session Startup

Before changing anything:

1. `README.md`
2. `course/syllabus.md`
3. `course/state.yaml`
4. The active lesson's `brief.md` and `handoff.md`
5. `docs/methodology.md`
6. `docs/agent-workflow.md`
7. Run `uv run python scripts/course_resume.py`.

Inspect the resume summary, `git status`, and any post-checkpoint diff. Present
the current lesson, latest checkpoint, worktree state, and next action to the
learner, then wait for confirmation before continuing. Never discard or
auto-commit post-checkpoint changes. Treat tracked course state as authoritative
over prior chat summaries.

## Scope

- Work on one bounded lesson or infrastructure task at a time.
- Do not silently broaden the research question.
- Do not infer tactical causes from event data alone.
- Do not commit files under `data/external/` or `data/processed/`.
- Do not add a heavy dependency until a current lesson needs it.
- Core lessons must run on local CPU.
- Preserve user-authored findings and unrelated working-tree changes.

## Lesson Contract

Before coding, ensure the active lesson has a concrete question, unit of
analysis, comparison baseline, outcome, required fields, assumptions, and
acceptance criteria in `brief.md`.

During implementation:

- Keep reusable loading, validation, metrics, and plotting logic under `src/`.
- Use notebooks for orchestration, inspection, and narrative.
- Prefer explicit metric definitions over opaque helper calls.
- Add tests proportional to the analytical risk.
- Make randomness deterministic.
- Record the upstream open-data commit in completed findings.

Before finishing:

- Restart and execute notebooks top-to-bottom.
- Run the validation commands required by the lesson and repository.
- Update `findings.md`, `checks.md`, `exercises.md`, and `handoff.md`.
- Update `course/state.yaml` only when global navigation changes.

## Checkpoints

Start a lesson on `lesson/<lesson-id>` and initialize `CP-000`. Create another
checkpoint after a meaningful learning unit: fixed data scope, a reusable
module, a validated notebook section, a principal chart, updated
findings/checks, or an explicit pause or learner decision.

Checkpoint order is fixed:

1. Update the single lesson `handoff.md` snapshot and append its concise
   history entry.
2. Run targeted checks for that learning unit.
3. Inspect the diff and preserve unrelated learner changes.
4. Commit locally as
   `checkpoint(<lesson-id>): CP-NNN <step>`.

Do not push during a lesson. A `paused` or `blocked` checkpoint may contain
incomplete work, but the handoff must name checks that were not run or failed.

## Explanation Contract

For every material output, explain:

1. What question it answers.
2. What rows, events, or samples went into it.
3. How it was calculated.
4. How to read it in football terms.
5. What it does not establish.
6. What check would make the conclusion more credible.

Label claims using the evidence ladder in `docs/methodology.md`: data fact,
metric result, football interpretation, or unverified hypothesis.

## Validation

Default repository checks:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python scripts/validate_course.py
uv run python scripts/course_resume.py
uv run python scripts/validate_notebook.py course/templates/analysis.ipynb
```

For a changed notebook, also execute it from a clean kernel. Never claim a
lesson is complete from a successful cell run in an existing interactive
kernel.

## Handoff

The handoff frontmatter is the latest resumable snapshot. Its body must state:

- completed work and changed files;
- decisions and definitions introduced;
- validation commands and results;
- unresolved questions or limitations;
- concise checkpoint history.

Do not leave essential context only in the chat transcript.

At lesson end, checkpoint `review`, run full validation, and explain the
outputs to the learner. After the learner accepts completion, checkpoint
`completed`, update global navigation, push the lesson branch, open one lesson
PR, and observe CI. Squash merge only after explicit merge confirmation.
