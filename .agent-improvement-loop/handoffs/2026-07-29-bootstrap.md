# Codex Handoff: Repository Bootstrap

## Goal

Provide a public, reproducible football analytics course repository that can
resume without prior chat context.

## Completed

- Initialized Git and published `https://github.com/apue/football-analytics`.
- Created and locked the Python 3.12 `uv` environment.
- Added the staged syllabus, methodology, data guide, lesson templates, Agent
  contract, and durable course state.
- Installed the Jupyter Notebook Skill in the current Codex environment.
- Created an ignored sparse partial clone of Hudl open data at commit
  `b0bc9f22dd77c206ddedc1d742893b3bbe64baec`.
- Added path helpers, course validation, notebook validation, sync behavior,
  tests, lint, and public-repository hygiene rules.

## Decisions

- The repository is public; upstream and generated data remain untracked.
- Core lessons target local CPU.
- Repository files, not chat history or tool-specific Skills, are the durable
  handoff source.
- Later syllabus details are elaborated near the point of use.

## Validation

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python scripts/validate_course.py
uv run python scripts/validate_notebook.py course/templates/analysis.ipynb
```

All commands passed during bootstrap. Six tests passed, and the notebook
template executed from a clean kernel.

## Known Context

- Git HTTPS access to the upstream data repository timed out during bootstrap.
  The current ignored clone uses authenticated SSH; the public script defaults
  to HTTPS and supports `FOOTBALL_ANALYTICS_OPEN_DATA_URL`.
- Repository code and course materials use the MIT License. Hudl StatsBomb
  Open Data remains governed by its upstream terms and attribution rules.

## Next Action

Start lesson `00-01-orientation`: inspect `data/competitions.json`, summarize
available competitions and data types, and propose a first match based on data
completeness rather than team fame alone.
