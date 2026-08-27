# ACCEPTANCE

Status: accepted

## Done Definition

- [x] A health check distinguishes KeyPool, Firecrawl, target-page, content,
  and parser availability without exposing secrets.
- [x] A versioned manifest can acquire, cache, resume, and audit URL shards.
- [x] Provider output follows one documented envelope independent of transport.
- [x] Roster and match-row career adapters pass representative fixtures.
- [x] Cohort, observation-window, tier, establishment, and sustained rules are
  deterministic and covered by tests.
- [x] Validation quarantines incomplete or contradictory records instead of
  silently converting them to zero.
- [x] The project skill passes structural validation and an independent Luna
  forward test in an isolated run directory.
- [x] Barcelona data can complete the pipeline or the exact external-source
  blocker is reported by the gate without producing misleading analysis.
- [x] Validated derived data and a visual report are generated; incomplete
  adult coverage is visibly reported as a lower-bound prototype.

## Acceptance Criteria

1. A valid KeyPool configuration and simple public page pass service health
   without printing credential or base-URL values.
2. A Firecrawl response with outer success and source status 405 fails the
   target contract and cannot enter parsing.
3. Re-running an unchanged manifest reuses completed items without duplicates.
4. A player listed in several academy seasons appears once under the final
   roster season.
5. A player continuing after 2019-20 is not treated as a 2019-20 exit.
6. Cup, youth, and continental rows do not count as domestic senior league.
7. Incomplete coverage below a threshold produces `unknown`, not
   `not_reached`.
8. Thresholds 10, 15, and 20 derive from the same source facts.
9. A Luna worker returns paths and validation counts without modifying policy.

## Manual Review Checklist

- [x] Report claims follow the repository evidence ladder.
- [x] Report numbers reconcile to exported CSV/JSON artifacts.
- [x] Source coverage and unresolved records are visible.
- [x] A player outcome traces to exact source records.
- [x] The final interface is readable on desktop and mobile.

## Out of Scope

- Cross-academy causal comparison in the first run.
- Public deployment without explicit user confirmation.
