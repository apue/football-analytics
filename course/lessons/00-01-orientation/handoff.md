---
lesson_id: 00-01-orientation
stage: 0
status: ready
checkpoint_id: CP-000
current_step: Confirm the orientation lesson starting point
next_action: Inspect available data coverage and propose one match for learner review
updated_at: 2026-07-30T11:08:42+08:00
---

# Handoff

## Completed

- Repository bootstrap and course contract defined.
- Upstream data sync path established.
- Lesson question, inputs, outputs, and acceptance criteria written.
- Course resume and local checkpoint workflow initialized.

## Current Work

- The lesson is ready; no data-backed analysis has started.

## Decisions

- This lesson maps data before performing football performance analysis.
- The first match will be selected after inspecting actual open-data coverage.

## Validation

- `uv lock --check`: pass - lockfile is internally consistent.
- `uv run ruff format --check .`: pass - 35 files formatted.
- `uv run ruff check .`: pass - no lint findings.
- `uv run pytest`: pass - 19 tests.
- `uv run python scripts/validate_course.py`: pass - state v2, handoff, and
  templates are valid.
- `uv run python scripts/validate_notebook.py course/templates/analysis.ipynb`:
  pass - template executed from a clean kernel.
- No lesson analysis notebook has been created yet.

## Open Questions

- Which competition and match provide the clearest combination of events,
  lineups, and optional 360 data?

## Checkpoint History

- CP-000 | 2026-07-30T11:08:42+08:00 | ready | Initialize resumable lesson workflow
