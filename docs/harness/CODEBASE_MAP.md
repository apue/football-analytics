# CODEBASE_MAP

Status: bootstrap

## Key Directories

- `src/football_analytics/`: reusable Python package.
- `tests/`: package and repository contract tests.
- `scripts/`: data synchronization and repository validation commands.
- `course/syllabus.md`: curriculum map and prerequisites.
- `course/state.yaml`: current learning and handoff state.
- `course/lessons/`: lesson-specific work.
- `course/templates/`: required lesson artifact templates.
- `docs/`: methodology, data, agent workflow, and harness decisions.
- `data/external/`: ignored upstream source repositories.
- `data/processed/`: ignored reproducible derived data.
- `reports/`: reviewed public outputs.

## Entry Points

- `README.md`: human project entrypoint and bootstrap commands.
- `AGENTS.md`: coding-agent entrypoint.
- `course/state.yaml`: current course and handoff entrypoint.

## Tests

- `tests/`: package and course-contract tests.
- `scripts/validate_course.py`: standalone course-state schema check.
