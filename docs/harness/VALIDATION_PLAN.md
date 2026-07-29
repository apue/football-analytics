# VALIDATION_PLAN

Status: accepted

## Validation Mode

Selected modes: schema-check, smoke-test, contract-test, and manual-acceptance.

Reason: bootstrap risk is primarily reproducibility, repository hygiene, and
handoff correctness rather than complex runtime behavior.

## Commands

```bash
uv lock --check
uv run ruff check .
uv run pytest
uv run python scripts/validate_course.py
uv run python scripts/validate_notebook.py course/templates/analysis.ipynb
git status --short --ignored
git ls-files data
```

## Pass Criteria

- Every command exits successfully.
- Course state references an existing lesson and valid status.
- Template files and required handoff fields are present.
- External and processed data remain ignored.
- No secret, virtual environment, cache, or notebook checkpoint is tracked.

## Manual Checks

- [ ] Public README states data attribution and evidence boundaries.
- [ ] Syllabus progresses by football questions, not library features.
- [ ] Agent instructions distinguish implementation from interpretation.
- [ ] Core curriculum remains local-CPU compatible.
- [ ] GitHub remote is public and initial commit is visible.

## Known Gaps

- A data-backed lesson notebook will be validated when the first lesson begins.
- Cross-platform validation beyond the current macOS environment is deferred.
