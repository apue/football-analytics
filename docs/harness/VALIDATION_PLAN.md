# VALIDATION_PLAN

Status: accepted

## Validation Mode

Selected modes: strict-tdd, regression-test, schema-check, contract-test,
smoke-test, and manual-acceptance.

Reason: this change introduces deterministic parsers, validators, Git-history
matching, and recovery-state classification. Tests cover those contracts while
the CLI and repository checks provide end-to-end evidence.

## Commands

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python scripts/validate_course.py
uv run python scripts/course_resume.py
uv run python scripts/validate_notebook.py course/templates/analysis.ipynb
git status --short --ignored
git ls-files data
```

## Pass Criteria

- Every command exits successfully.
- State v2 references an existing lesson and contains navigation fields only.
- Handoff frontmatter, required sections, checkpoint format, and latest
  checkpoint-history entry are valid and consistent.
- Resume cases cover all allowed statuses, clean/dirty worktrees, mismatched
  lesson IDs, missing commits, and mismatched checkpoint IDs.
- The repository resume command identifies an existing local checkpoint.
- External and processed data remain ignored.
- No secret, virtual environment, cache, or notebook checkpoint is tracked.

## Manual Checks

- [x] Public README states data attribution and evidence boundaries.
- [x] Syllabus progresses by football questions, not library features.
- [x] Agent instructions distinguish implementation from interpretation.
- [x] Core curriculum remains local-CPU compatible.
- [x] GitHub remote is public and initial commit is visible.

## Known Gaps

- GitHub push, PR, CI observation, and squash merge are intentionally deferred
  until lesson review is accepted by the learner.
- A data-backed lesson notebook will be validated when the first lesson begins.
