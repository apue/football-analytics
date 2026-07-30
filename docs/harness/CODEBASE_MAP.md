# CODEBASE_MAP

Status: current

## Key Directories

- `src/football_analytics/`: reusable Python package.
- `tests/`: package and repository contract tests.
- `scripts/`: data synchronization and repository validation commands.
- `.github/workflows/`: pull-request and default-branch validation.
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
- `scripts/course_resume.py`: read-only session recovery summary.
- `src/football_analytics/course_progress.py`: state v2, handoff, checkpoint,
  and Git-inspection contracts.

## Tests

- `tests/`: package and course-contract tests.
- `scripts/validate_course.py`: standalone course-state schema check.
- `tests/test_course_progress.py`: course contract and recovery scenarios.

<!-- generated-codebase-map:start -->
## Generated Codebase Summary

- File count: 65

### Top Directories
- `docs`: 14 files
- `.ruff_cache`: 12 files
- `course`: 10 files
- `.`: 7 files
- `.pytest_cache`: 5 files
- `data`: 5 files
- `scripts`: 4 files
- `src`: 3 files
- `tests`: 3 files
- `.github`: 1 files
- `reports`: 1 files

### File Types
- `.md`: 25
- `<none>`: 20
- `.py`: 9
- `.TAG`: 2
- `.json`: 2
- `.lock`: 1
- `.toml`: 1
- `.yaml`: 1
- `.ipynb`: 1
- `.sh`: 1
- `.yml`: 1
- `.pdf`: 1
<!-- generated-codebase-map:end -->
