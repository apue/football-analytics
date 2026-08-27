# SPEC

Status: accepted

## Goal

Build a reusable, auditable academy-to-senior conversion pipeline. The first
validated source adapter and research run targets FC Barcelona Juvenil A, but
the data contracts and analysis must support other academies without changing
core logic.

The pipeline must acquire source pages through replaceable providers, preserve
raw evidence and provenance, parse deterministic roster and player-season
facts, validate coverage, build exit cohorts, classify competition levels, and
calculate configurable conversion outcomes. A project skill must allow a
small-model subagent to operate bounded shards without changing research rules.

## Users and Use Cases

- Learner: define the academy question, thresholds, league tiers, and interpret
  results.
- Operator agent: run acquisition, validation, analysis, and report generation
  reproducibly.
- Reviewer: trace every published result to a player-season row and source URL.

## Research Contract for the First Run

- Population: unique players listed in historical FC Barcelona Juvenil A/U19
  season rosters, regardless of youth appearances.
- Cohorts: a player's last listed Juvenil A season is 2015-16 through 2019-20.
- Boundary audit: later rosters are loaded so continuing players are not
  misclassified as exits.
- Observation: the five complete seasons after the last roster season.
- Outcome dimensions:
  - highest competition tier reached through a domestic senior-league
    appearance;
  - established: at least 15 domestic senior-league appearances in one season;
  - sustained: at least two seasons with at least 15 appearances;
  - sensitivity thresholds: 10, 15, and 20 appearances.
- Claims describe observed conversion after reaching the highest youth squad;
  they do not establish causal academy impact or represent all La Masia
  entrants.

## Functional Requirements

- Load KeyPool credentials without logging their values and normalize a base
  URL that omits a scheme.
- Support KeyPool-routed Firecrawl scrape and batch-scrape workflows.
- Treat transport success, Firecrawl success, target HTTP status, content
  contract, and parser success as separate states.
- Persist idempotent URL manifests, raw responses, content hashes, attempts,
  costs when available, and failure records.
- Keep the acquisition provider replaceable; allow fixture/manual imports when
  a target blocks Firecrawl.
- Parse rosters and player-season competition rows deterministically.
- Store source facts before assigning analytical tiers.
- Use stable player identifiers for cross-season deduplication.
- Build exit cohorts and exactly five following observation seasons.
- Apply versioned competition-tier configuration without changing raw facts.
- Emit coverage and validation reports before analysis.
- Produce complete player, player-season, outcome, cohort-summary, provenance,
  and sensitivity data artifacts.
- Provide a project-level skill and bounded worker protocol for subagents.

## Non-Functional Requirements

- Local CPU only; Python standard library preferred for the core pipeline.
- Every deterministic transformation has focused tests.
- Re-running an unchanged stage is idempotent and uses cached evidence.
- Workers write disjoint shard directories; deterministic merge owns shared
  outputs.
- Secrets, raw authentication material, and browser state never enter logs or
  Git.
- External terms, robots policy, rate limits, and source attribution are
  recorded before bulk acquisition.
- Repository rules for `data/external/` and `data/processed/` remain intact.

## Non-Goals

- Estimating causal player development added by an academy.
- Scouting or predicting latent player ability.
- Using an LLM for counting, joins, threshold calculations, or aggregation.
- Automatically bypassing anti-bot, access-control, or source-use restrictions.
- Guaranteeing support for every football statistics website in version one.

## Isolated Questions

- The first roster source is now the official FC Barcelona annual-report
  archive. Transfermarkt automated collection is prohibited without written
  permission and is not a fallback provider.
- No license-clear free source with complete global T1/T2 adult appearance
  coverage has been identified. The adult-career stage must use a licensed
  source, documented official sources, or an explicitly narrower scope.
- Redistribution rights for any adult appearance source must be resolved before
  public hosting; local complete research data remains required.

## Acceptance Link

See `ACCEPTANCE.md`.
