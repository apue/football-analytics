# SPEC

Status: accepted

## Goal

Bootstrap a public, reproducible football analytics learning repository that
combines analyst-style questions with progressively deeper statistics and
machine learning. Coding agents implement and explain the work; the learner
owns the question, assumptions, interpretation, and evidence review.

The course workflow must also recover safely across Codex sessions. One lesson
is active at a time, each meaningful learning unit ends in a local checkpoint
commit, and a new session reports the latest durable checkpoint plus any
uncommitted work before the learner chooses whether to continue.

## Non-Goals

- Reproduce video or tracking analysis from event data.
- Commit the Hudl StatsBomb open-data repository or generated datasets.
- Install deep-learning frameworks or require cloud compute at bootstrap.
- Fully script every future lesson before learning feedback exists.

## Users and Use Cases

- Learner: follows guided case studies, reviews generated code, interprets
  outputs, and gradually takes ownership of research questions.
- Coding agent: resumes from repository state, implements one bounded lesson,
  validates it, explains outputs, and leaves a durable handoff.
- Reader: can reproduce public analyses from a clean clone and independently
  inspect definitions, evidence, and limitations.

## Requirements

### Functional

- Manage Python and dependencies with `uv`.
- Keep Hudl StatsBomb open data as an ignored, independently synchronized
  shallow partial clone with sparse checkout under `data/external/`.
- Define a staged syllabus from event-data literacy through independent
  modeling and a capstone.
- Provide reusable lesson, findings, checks, exercises, and notebook templates.
- Persist course progress and next actions in a machine-readable state file.
- Keep global course state limited to navigation and keep the active lesson's
  status, checkpoint, current step, next action, and history in one handoff.
- Provide a read-only resume command that checks state/handoff consistency,
  Git branch and cleanliness, and whether the handoff checkpoint exists in
  local history.
- Validate the state v2 and handoff frontmatter contracts.
- Define provider-neutral agent startup, execution, validation, explanation,
  and handoff rules.
- Provide a small importable Python package and tests as the base for reusable
  analysis code.

### Non-Functional

- A fresh clone must be recoverable without prior chat history.
- An interrupted local session must distinguish the last checkpoint from later
  uncommitted work without discarding or committing that work automatically.
- Notebooks must be restartable and executable top-to-bottom.
- Definitions and data limitations must accompany analytical outputs.
- CPU is the default compute target; optional GPU work must not block the core
  curriculum.
- Public-repository hygiene must exclude raw external data, generated data,
  secrets, caches, and private machine state.

## Constraints

- The primary data source is public Hudl StatsBomb open data.
- Event data does not observe continuous off-ball behavior.
- The initial GitHub repository is public under the authenticated account.

## Deferred Questions

- Which Premier League season or alternative competition becomes the first
  season-level case depends on actual open-data availability.
- Exact later-stage models will be refined after the descriptive and
  statistical foundations are complete.

## Acceptance Link

See `ACCEPTANCE.md`.
