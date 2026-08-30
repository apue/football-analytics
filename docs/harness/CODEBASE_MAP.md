# Codebase map

- `src/football_analytics`: dependency-free reusable Python package.
- `tests`: deterministic tests; network calls must be stubbed unless explicitly
  running the online E2E command.
- `.codex/skills`: repository-local reusable operating guidance.
- `config`: committed frozen research and search configuration.
- `data/external`, `data/processed`: ignored runtime data; never committed.
- `course`: active learning progression; this infrastructure change does not
  advance the current lesson.
