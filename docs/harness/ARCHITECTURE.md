# ARCHITECTURE

Status: accepted

## Summary

The repository separates immutable upstream data, reusable analysis code,
lesson narratives, and generated outputs. The repository itself is the durable
source of truth for both learners and coding agents.

## Boundaries

- `data/external/`: ignored upstream repositories and immutable source data.
- `data/processed/`: ignored reproducible transformations.
- `src/football_analytics/`: tested reusable loading, validation, metric, and
  visualization code.
- `course/`: syllabus state, lesson briefs, learner-facing outputs, and
  templates.
- `reports/`: finished public reports and figures selected for publication.
- `docs/`: methodology, data contracts, agent workflow, and project harness.

Notebooks orchestrate and explain analysis. They must not become the only home
for reusable definitions or calculations.

## Data and Control Flow

1. Clone or update Hudl open data independently under `data/external/`, then
   materialize only the files required by the active lesson.
2. Read source JSON without mutating it.
3. Validate schema assumptions and transform reproducibly in package code.
4. Execute a lesson notebook using package functions.
5. Record findings, checks, limitations, and exercises beside the lesson.
6. Update the lesson `handoff.md`, run targeted checks, inspect the diff, and
   create a local checkpoint commit for a meaningful learning unit.
7. Promote only finished, reviewed outputs into `reports/`.

## Agentic Harness Components

- Instructions: `AGENTS.md` is the portable entrypoint.
- Routing/handoffs: `course/state.yaml` identifies the sole active lesson;
  that lesson's `handoff.md` owns resumable status and next-action detail.
- Resume inspection: `src/football_analytics/course_progress.py` owns parsing,
  validation, and Git inspection; `scripts/course_resume.py` is a thin,
  read-only command-line adapter.
- Memory/context: tracked lesson artifacts and Git history, not chat history.
- Guardrails: evidence labels, notebook restartability, tests, lint, and
  validation commands.
- Output contract: each lesson separates brief, implementation, findings,
  checks, and exercises.

## Alternatives Considered

- Git submodule for open data: rejected initially because it adds learner-facing
  Git friction. An ignored shallow partial clone plus a sync script is simpler.
- Full open-data checkout: rejected because the upstream repository is several
  gigabytes and the curriculum only needs selected competitions at a time.
- Skills as the source of agent behavior: rejected because support differs
  across coding agents. Skills remain optional adapters.
- Fully detailed long-range curriculum: rejected because later lessons should
  respond to actual learning and data availability.
- Cloud-first notebooks: rejected because ephemeral environments weaken local
  reproducibility and are unnecessary for core event-data work.

## Risks

- Analytical overclaiming: require separation of data fact, metric result,
  football interpretation, and unverified hypothesis.
- Notebook drift: move reusable logic to `src/` and execute notebooks from a
  clean kernel.
- Upstream data changes: keep source commit visible and update explicitly.
- Agent context loss: make state and next actions mandatory tracked artifacts.
- Handoff/Git drift: validate the latest checkpoint-history entry and compare
  the frontmatter checkpoint with local checkpoint commit subjects.
- Dependency growth: use optional `uv` groups and add heavy packages only when
  a lesson requires them.
