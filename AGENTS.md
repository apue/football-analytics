# Agent Working Agreement

This repository is a learning system, not a notebook dump. The learner owns the
football question, assumptions, interpretation, and final claims. The agent
owns implementation quality, reproducibility, validation, and clear
explanation.

## Session Startup

Read these files before changing anything:

1. `README.md`
2. `course/syllabus.md`
3. `course/state.yaml`
4. The active lesson's `brief.md` and `handoff.md`
5. `docs/methodology.md`
6. `docs/agent-workflow.md`

Then inspect `git status` and the relevant existing code. Treat tracked course
state as authoritative over prior chat summaries.

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
- Update `course/state.yaml`, including the exact next action.

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
uv run ruff check .
uv run pytest
uv run python scripts/validate_course.py
```

For a changed notebook, also execute it from a clean kernel. Never claim a
lesson is complete from a successful cell run in an existing interactive
kernel.

## Handoff

The final handoff must state:

- completed work and changed files;
- decisions and definitions introduced;
- validation commands and results;
- unresolved questions or limitations;
- one concrete next action.

Do not leave essential context only in the chat transcript.
