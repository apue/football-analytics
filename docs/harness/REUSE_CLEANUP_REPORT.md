# REUSE_CLEANUP_REPORT

Status: complete

## Search Evidence

- The workspace was empty before harness initialization.
- No existing package, notebook, data, test, or project convention was present.

## Reuse

- Use `uv` for environment and lockfile management.
- Use Hudl StatsBomb open data as an independent upstream repository.
- Use `mplsoccer` and `matplotlib` for football-native visualization.
- Use `pandas`, `scikit-learn`, and `statsmodels` when lessons require them.
- Use the installed Jupyter Notebook Skill as an optional Codex adapter.

## Cleanup

No deprecated project logic exists.

## Decision

Create the minimum new project structure needed for reproducible lessons,
durable handoff, and tested reusable analysis code.
