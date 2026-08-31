# Validation plan

## Modes

- Contract tests: evidence request/response and artifact boundary.
- Regression tests: academy calculations and Barcelona frozen baseline.
- Schema checks: study, search configuration, and skill packages.
- Online smoke/E2E: one controlled Barcelona search through the direct
  Firecrawl API.
- Review: independent Standards and Spec code review after CI.

## Commands

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv lock --check
git diff --check origin/main...HEAD
```

Skill validation uses `quick_validate.py` for each changed skill. The online
command writes only below ignored `data/processed/`.

## Pass criteria

All offline commands pass; the online response validates and is preserved; the
canonical evidence comparison is reported; the frozen academy analysis matches
its expected counts; CI and both review axes have no unresolved blockers.
