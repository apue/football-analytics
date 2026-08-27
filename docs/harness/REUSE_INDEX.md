# REUSE_INDEX

Status: accepted

## Reusable Capabilities

- Capability: explicit data-source status and atomic derived outputs
  - Path: `src/football_analytics/catalog.py`
  - How to reuse: mirror status envelopes and safe rebuild patterns.
  - Tests: `tests/test_catalog.py`
- Capability: pure summary plus separate writers
  - Path: `src/football_analytics/season_xg.py`
  - How to reuse: keep calculations independent from files and CLI.
  - Tests: `tests/test_season_xg.py`

## Extension Points

- Extension point: CLI registration
  - Path: `pyproject.toml`
  - Contract: thin CLI delegates to tested library functions.
- Extension point: publishable report root
  - Path: `reports/`
  - Contract: derived, attributed artifacts only.

## Avoid Parallel Implementations

- Existing capability: project paths and data boundaries
  - Prefer: root discovery and ignored processed-data conventions.
  - Avoid: hard-coded machine paths or committed raw caches.

## Generated Candidates

The `refresh_reuse_index.py` script may append candidate files below.

<!-- generated-reuse-index:start -->
## Generated Reuse Candidates

- `.codex/hooks.json`
- `.codex/hooks/course_turn_stop.py`
<!-- generated-reuse-index:end -->
