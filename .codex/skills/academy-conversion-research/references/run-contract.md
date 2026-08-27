# Run contract

## Immutable configuration

Each run records an academy ID, roster source adapter, roster seasons used for
boundary detection, exit-cohort range, observation-season count, thresholds,
competition-policy version, provider, and source-policy status.

Barcelona version one uses roster seasons 2015-16 through at least 2021-22,
selects final roster seasons 2015-16 through 2019-20, observes five following
complete seasons, and evaluates thresholds 10, 15, and 20 with 15 primary.

## Stage state

```text
configured -> manifested -> acquired -> parsed -> validated -> analyzed -> rendered
```

No stage may consume an unvalidated upstream artifact. Per-item states are:

```text
pending | complete | retryable_failed | permanent_failed |
validation_failed | parse_failed | quarantined
```

## Data contracts

- Roster candidate: academy, season, displayed name, source URL and page. Do not
  infer a stable player ID from a name.
- Identity resolution: roster candidate, stable player ID, review status, and
  evidence. Only uniquely confirmed mappings become roster facts.
- Roster fact: academy, season, stable player ID, displayed name, source URL.
- Appearance fact: player, season, club, competition, appearances, source URL.
- Competition rule: competition and season, tier, rank, domestic-senior
  eligibility, policy version.
- Coverage fact: player and observation season, complete/partial/missing.

Store facts before deriving tiers or outcomes. A player belongs to the final
observed roster season only. Observation seasons are the next five season-start
years. Different competition tiers never combine to cross a seasonal threshold.

The canonical fields and CLI boundaries are documented in
`docs/academy-conversion-data-contract.md`.

## Shared-state rule

Workers write only `shards/<shard-id>/`. The supervisor alone writes merged,
validated, derived, and report artifacts.
