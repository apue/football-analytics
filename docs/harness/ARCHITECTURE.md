# ARCHITECTURE

Status: accepted

## Summary

The pipeline is a file-backed state machine with deterministic stages:

```text
configure -> manifest -> acquire -> parse -> validate -> analyze -> render
```

External acquisition is isolated behind a provider envelope. LLM workers
operate scripts and adjudicate quarantined exceptions; they do not own numeric
transformations or shared output files.

## Boundaries

- `football_analytics.web_acquisition`: provider envelopes, KeyPool/Firecrawl
  transport, cache identities, health and content contracts.
- `football_analytics.academy_conversion`: source-neutral schemas, cohort and
  observation windows, tier rules, validation, and outcome calculation.
- `football_analytics.academy_conversion_cli`: deterministic command entry
  point, registered as `academy-conversion` in `pyproject.toml`.
- `.codex/skills/academy-conversion-research`: routing, workflow, stop gates,
  worker handoff contract, and thin helper scripts.
- `data/processed/academy-conversion/runs/<run-id>`: ignored run state, raw
  evidence, parsed rows, quarantine records, and derived outputs.
- `data/processed/academy-conversion/runs/<run-id>/report`: local visual report;
  public publication is a separate, explicitly approved action.

## Provider Envelope

Every acquisition provider emits URL, provider, retrieval time, transport and
target status, success state, content path and hash, attempt, cache state, and
error classification. Parsers consume only validated content paths.

## Run Layout

```text
run/
  sources/<source>/records/*.json
  sources/<source>/raw/<provider>/<url-hash>/attempt-*.pdf
  parsed/<adapter>/roster_candidates.csv
  validated/roster_memberships.csv
  shards/<worker-id>/{validation,handoff}.json
  prototype/<adapter>/facts/*.csv
  prototype/<adapter>/analysis/*.csv
  report/index.html
```

## Multi-Agent Topology

- Supervisor freezes configuration, creates manifests, assigns shards,
  validates merges, and owns conclusions.
- Luna workers execute one immutable shard, inspect only quarantined items, and
  return a structured handoff.
- Filesystem artifacts, not paraphrased page content, carry shared state.
- Start with at most two acquisition workers; scale only after measurement.

## Guardrails

- No bulk run until representative target content contracts pass.
- Firecrawl outer success alone never validates a raw page.
- Do not retry policy blocks, authentication failures, or permanent 4xx.
- Bound retries for transient timeouts, 429, and 5xx responses.
- Persist transport exceptions as `retryable_failed` attempt records; one CLI
  invocation makes one bounded attempt so an operator controls subsequent
  retries.
- Workers cannot change config, tier policy, parsers, or shared result files.
- Missing observations cannot become zero without complete coverage.

## Alternatives Considered

- LLM-per-page extraction: rejected; exact tables require deterministic parsing.
- Transfermarkt-only core: rejected; source access can change.
- Database-first orchestration: deferred in favor of auditable file runs.
- One agent per player: rejected due coordination and token cost.

## Risks and Mitigations

- Target blocking: stop at content gate; use an allowed provider or import.
- Coverage gaps: explicit states and outcome bounds.
- Parser drift: golden fixtures, content hashes, and schema checks.
- Source terms: preflight policy record before acquisition or publishing.
- Model propagation: workers return paths; validators decide acceptance.
