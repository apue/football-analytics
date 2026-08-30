# Academy conversion data contract

Version: 1

The pipeline separates source facts, identity review, analytical policy, and
derived outcomes. Missing data is never encoded as zero.

## Acquisition record envelope

Every provider writes the same auditable record fields: `url`, `provider`,
`retrieved_at`, `transport_status`, `provider_status`, `target_status`,
`status`, `content_path`, `content_sha256`, `attempt`, `cache_state`,
`error_classification`, `cost`, and `error`. `cost` is null when the provider
does not report one. A returned cached result changes `cache_state` from
`miss` to `hit` without rewriting the original attempt record.

`complete` and non-retryable `validation_failed` records are cacheable.
`retryable_failed` is reserved for transient transport failures, HTTP 408/429,
and 5xx target responses. Permanent 4xx, provider-response failures, and
content-contract failures require operator investigation rather than automatic
retries.

Firecrawl batch mode persists the untouched start and status responses under
`raw/firecrawl-batch/`, plus a resumable job record under `batches/`. A later
invocation resumes a queued or processing job. Completed documents are mapped
to their manifest URLs and then written through the same per-item envelope and
content validation used by single-page acquisition.

## Roster identity boundary

Official academy sources often publish names without stable person IDs. A
roster parser therefore emits `roster_candidates.csv` first:

| field | meaning |
| --- | --- |
| `candidate_id` | stable ID derived from source, academy, season, and row |
| `displayed_name` | name exactly as shown by the source |
| `academy_id` | stable academy/squad ID |
| `season_start` | start year of the roster season |
| `source_url` | exact evidence URL |
| `source_page` | one-based PDF page or equivalent source location |
| `position` | source role normalized to goalkeeper/defender/midfielder/forward |

Identity review produces `identity_resolutions.csv` with `candidate_id`,
`player_id`, `status`, and `evidence`. Allowed review states are `confirmed`,
`unresolved`, and `ambiguous`. Only one uniquely `confirmed` mapping with a
non-empty stable `player_id` becomes a roster membership. The command is:

```bash
uv run academy-conversion resolve-rosters \
  --candidates roster_candidates.csv \
  --resolutions identity_resolutions.csv \
  --output roster_memberships.csv \
  --validation identity-validation.json
```

## Analysis inputs

- `config/academy_conversion/studies/<study-id>.json`: academy and squad
  identity, cohort and observation windows, thresholds, sustained-season count,
  competition-policy path, roster-source config, source policy, run directory,
  and report metadata
- `roster_memberships.csv`: `player_id,player_name,academy_id,season_start,source_url`
- `appearances.csv`: `player_id,season_start,club_id,competition_id,appearances,source_url`
- `competitions.csv`: `competition_id,season_start,tier,tier_rank,eligible_domestic_league,policy_version`
- `coverage.csv`: `player_id,season_start,status,scope_id,source_url`, where
  status is `complete`, `partial`, or `missing`

An appearance row is one player-club-competition-season fact. The analysis
sums clubs within the same season and analytical tier, but never combines
different tiers to cross a threshold. Competition eligibility and tier are
versioned policy, not source facts.

The JSON competition policy may also provide static `competition_metadata`
with `country`, `domestic_level`, `name_zh`, and `career_eligible`. These fields
support reader-facing league names and the professional-career view without
changing raw appearance facts. The first version is intentionally static;
future policies may add season validity fields when historical reclassification
materially affects a result.

`reporting_bands` independently defines nested reader-facing outcome groups.
A band with `tiers: null` contains every competition whose rule has
`eligible_domestic_league=true`; narrower bands list accepted achievement tiers.
This keeps “professional career” separate from “competitive height”.

`complete` coverage means all competitions in the declared scope were checked
for that player-season, including verified zero appearances. `partial` means
some scope was checked. `missing` means the required scope was not checked.
An absent coverage row is also unknown.

Acquisition, roster parsing, fact construction, analysis, and rendering load the
same study config. Commands reject a different academy, roster-season window,
source config, run directory, or output path outside that run directory.
The analysis gate also requires each roster season's membership count to equal
the frozen source page `expected_player_count`, including later boundary-audit
seasons, before building exit cohorts.

## Analysis outputs

`academy-conversion analyze` validates input keys and values before deriving:

- `exit_cohorts.csv`: one player under their final observed academy season;
- `player_threshold_outcomes.csv`: one player per 10/15/20 threshold;
- `cohort_summary.csv`: raw numerator, total denominator, classified count,
  complete-coverage denominator, unknown count, complete-coverage rate, and
  conservative all-player lower-bound rate;
- `validation.json`: machine-readable issues and analysis readiness.
- `provenance.json`: exact input artifact paths, distinct source URLs, and
  competition-policy versions used by the run.

Observed positives remain valid under partial coverage, but a rate is not
declared complete unless every cohort member has complete coverage. The
all-player rate is a lower bound while unknowns remain.
