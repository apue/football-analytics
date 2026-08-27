---
name: academy-conversion-research
description: Build or operate the repository's auditable academy-to-senior conversion pipeline, including source health checks, roster and career acquisition, deterministic parsing, cohort validation, competition-tier outcomes, bounded worker shards, and report data. Use for youth-academy conversion studies such as Barcelona Juvenil A. Do not use for match-event analysis or scouting predictions.
---

# Academy Conversion Research

Use the repository pipeline as the source of truth. Scripts acquire, parse,
validate, and calculate; agents operate bounded work and explain exceptions.

## Select a mode

- **Supervisor mode:** create or approve a run, freeze configuration, assign
  shards, merge validated outputs, and own research claims.
- **Worker mode:** execute one existing immutable shard and return a handoff.
  Do not edit configuration, tier policy, parsers, or shared outputs.
- **Source-adapter mode:** diagnose or add one provider/page parser. Use golden
  fixtures and contract tests before enabling it for a run.

Read [run-contract.md](references/run-contract.md) for every mode. In worker
mode also read [worker-handoff.md](references/worker-handoff.md). When a run
touches an external site, read [provider-policy.md](references/provider-policy.md).

## Required workflow

1. Inspect the run configuration and validation state. Never reconstruct
   research rules from chat or page content.
2. Run `uv run academy-conversion health` before creating a live acquisition
   manifest. A service pass is insufficient: the target content contract must
   pass.
3. Stop bulk acquisition when policy approval is absent, target status is not
   2xx, required content is missing, or the parser golden fixture fails.
4. Acquire only URLs in the assigned manifest or shard. Reuse complete cached
   items and preserve all attempts.
5. Run parsing and validation scripts. A roster worker emits candidates with
   source pages; it never guesses stable player IDs. The supervisor reviews an
   identity-resolution table before roster facts can be merged. Do not
   manually copy page counts into shared CSV files.
6. Inspect only records in the exception queue. Record evidence and a proposed
   disposition; do not convert missing data to zero.
7. The supervisor runs deterministic merge and analysis after every shard
   validates.
8. Report artifact paths, counts, failures, and unrun checks. Never report a
   conversion rate from an incomplete or unvalidated run.

## Canonical commands

Use `uv run academy-conversion --help` as the command inventory. The main
stage commands are `manifest`, `acquire`, `validate-run`,
`parse-official-rosters`, `resolve-rosters`, `merge-source-link-proposals`,
`build-match-row-prototype`, `analyze`, and `render-report`.

`merge-source-link-proposals` accepts only reviewed `confirmed` proposals and
fails on unknown players, duplicate proposals, identity conflicts, or reused
source IDs. `--source-players` is required so every proposed external ID is
verified against the exact source snapshot. It ignores unresolved proposals.
Run `analyze` only after this supervisor-owned merge and its upstream
validations pass.

The dcaribou adapter is a technical prototype, not a complete career source.
It emits `partial` or `missing` coverage only. Its observed positives may be
reported as conservative lower bounds; its unknown rows must never be relabeled
as failures or used to claim a complete conversion rate.

## Model boundary

Use a small model for bounded acquisition execution, page-structure diagnosis,
identity conflicts, source conflicts, and narrative drafts from validated
summary JSON. Use code for joins, season windows, competition eligibility,
thresholds, aggregation, and percentages.

## Safety and provenance

- Load credentials only from the requested env file; never print their values.
- Use `KEYPOOL_KEY` as the bearer token and `KEYPOOL_URL` as the base URL. The
  client adds `x-keypool-service: firecrawl`.
- Do not bypass access controls or retry permanent/policy failures.
- Preserve source URL, retrieval time, target status, content hash, and provider
  on every accepted record.
- Raw acquisition belongs under ignored `data/processed/` run directories.
- Public output must follow the source policy and repository attribution rules.

## Stop conditions

Stop and return a structured handoff when the target contract fails, the source
policy is unresolved, an assigned shard would overlap another worker, validation
cannot distinguish absence from missing coverage, or completing the task would
require changing frozen research rules.
