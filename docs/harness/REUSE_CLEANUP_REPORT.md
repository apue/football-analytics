# REUSE_CLEANUP_REPORT

Status: updated

## Existing Capabilities

- `scripts/validate_course.py` already loads YAML, checks the active lesson,
  and validates required templates. Extend its entry point while moving the
  reusable state and handoff contract into the package.
- `src/football_analytics/paths.py` establishes the project-root convention.
  Reuse the same repository layout, but keep course-progress functions
  independently testable with an explicit root.
- Existing pytest and CI commands already exercise package and repository
  contracts. Extend them rather than add another test runner.

## Search Evidence

- Searched `state.yaml`, `handoff`, `validate_course`, `checkpoint`,
  `current_lesson`, `next_action`, and `schema_version` across the repository.
- Inspected `scripts/validate_course.py`, `course/templates/handoff.md`,
  `course/state.yaml`, `AGENTS.md`, `docs/agent-workflow.md`, and CI.

## Reuse

- Reuse PyYAML, pathlib, subprocess, pytest, the existing validation command,
  and the existing CI quality job.
- Keep `scripts/course_resume.py` as a thin adapter over package code so tests
  can cover temporary repositories without subprocess-heavy fixtures.

## Cleanup

- Remove schema v1 fields `status`, `next_action`, `open_questions`, and
  `last_updated` from global state.
- Replace the old heading-only handoff format with YAML frontmatter plus the
  required snapshot/history sections.
- Replace duplicated state parsing in `scripts/validate_course.py` with the
  reusable package contract.

## Decision

- Extend the existing validator and test/CI paths.
- Add one new reusable package module and one read-only CLI.
- Do not add dependencies or a separate journal.

## Risks

- Commit lookup must not mistake unrelated lesson commits for the active
  checkpoint; match the exact lesson ID and checkpoint subject format.
- Dirty status must include untracked files and must remain read-only.
- Frontmatter/history parsing must fail with actionable messages rather than
  silently accepting partial handoffs.
