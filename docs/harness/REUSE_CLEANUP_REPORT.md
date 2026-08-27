# REUSE_CLEANUP_REPORT

Status: accepted

## Existing Capabilities

- `src/football_analytics/catalog.py`: reuse explicit status reporting, stable
  IDs, read-only posture, and atomic derived-data conventions; reject its
  StatsBomb-specific schema.
- `src/football_analytics/paths.py`: extend only if a repository-wide academy
  run-root resolver is needed.
- `src/football_analytics/season_xg.py`: reuse separation of pure summaries and
  file writing; do not mix the unrelated xG domain.
- `.codex/hooks/course_turn_stop.py`: retain checkpoint behavior.

## Extension Points

- `src/football_analytics/__init__.py`: export stable public functions only.
- `pyproject.toml [project.scripts]`: add one CLI entry point.
- `reports/`: add final visual output without changing active lesson files.

## Deprecated or Removable Logic

None. This capability does not replace active lesson logic.

## Search Evidence

Inspected `pyproject.toml`, source/test skeletons, report directory, branch
history, and repository instructions. Searched existing report, academy,
Transfermarkt, and web-acquisition implementations; none matched this lifecycle.

## Decision

- Reuse repository validation and pure-function conventions.
- Extend CLI registration and public exports only as needed.
- Add provider-neutral acquisition and academy-conversion modules.
- Add a project skill and report surface.
- Delete or deprecate nothing.

## Risks

- Work occurs in an isolated worktree from `main` to preserve the unrelated xG
  branch.
- External source access and licensing are primary blockers.
