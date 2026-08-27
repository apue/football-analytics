# CODEBASE_MAP

Status: accepted

## Overview

Python package with deterministic football-data loading and validation, lesson
artifacts under `course/`, ignored external/processed data, and publishable
outputs under `reports/`. The academy pipeline is separate from the active
spatial-quality lesson.

## Key Directories

- `src/football_analytics/`: reusable deterministic library code.
- `tests/`: synthetic and fixture-backed tests.
- `scripts/`: repository orchestration helpers.
- `.codex/skills/`: repository-local operating skills.
- `data/processed/`: rebuildable ignored run state.
- `reports/`: publishable research outputs.

## Entry Points

- `pyproject.toml [project.scripts]`: CLI registration.
- `src/football_analytics/*_cli.py`: command entry points.

## Tests

- `tests/`: pytest unit, contract, and integration tests.

## Generated Section

The `refresh_reuse_index.py` script may append or update summary content below.

<!-- generated-codebase-map:start -->
## Generated Codebase Summary

- File count: 82

### Top Directories
- `course`: 26 files
- `docs`: 14 files
- `src`: 9 files
- `.`: 8 files
- `.codex`: 8 files
- `tests`: 6 files
- `references`: 3 files
- `scripts`: 3 files
- `data`: 2 files
- `.github`: 1 files
- `config`: 1 files
- `reports`: 1 files

### File Types
- `.md`: 40
- `.py`: 17
- `<none>`: 8
- `.yaml`: 4
- `.ipynb`: 4
- `.json`: 3
- `.toml`: 2
- `.sh`: 2
- `.lock`: 1
- `.yml`: 1
<!-- generated-codebase-map:end -->
