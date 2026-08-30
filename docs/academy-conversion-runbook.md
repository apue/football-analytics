# Academy conversion pipeline runbook

This runbook operates the reusable academy-to-senior pipeline. Barcelona
Juvenil A is the first adapter; research rules live in configuration and data
contracts rather than in agent prompts.

## Stage order

```text
approve source -> manifest -> acquire -> validate -> parse roster
-> resolve identities -> build adult facts -> validate/analyze -> render
```

The CLI inventory is available with:

```bash
uv run academy-conversion --help
```

Before creating a live manifest, run `academy-conversion health` against one
representative target. Its JSON `checks` object reports KeyPool configuration,
transport, Firecrawl response, target HTTP status, content contract, and the
built-in roster-parser probe separately. Later gates remain `not_checked` after
an earlier failure, so an operator can see the exact boundary that stopped the
run. The parser probe is a deterministic golden input; the source-specific
parser and expected roster count are still checked during
`parse-official-rosters`.

Official roster reports use
`config/academy_conversion/barcelona_juvenil_a_rosters.json`. Generate and
acquire its manifest, require `validate-run` to pass, then parse with:

```bash
uv run academy-conversion manifest \
  --study-config config/academy_conversion/studies/<study-id>.json \
  --config <roster-source-config> \
  --output <configured-run-dir>/manifest.jsonl
uv run academy-conversion acquire \
  --study-config config/academy_conversion/studies/<study-id>.json \
  --config <roster-source-config> \
  --manifest <configured-run-dir>/manifest.jsonl \
  --run-dir <configured-run-dir>
uv run academy-conversion validate-run \
  --study-config config/academy_conversion/studies/<study-id>.json \
  --run-dir <configured-run-dir>
uv run --with pymupdf academy-conversion parse-official-rosters \
  --study-config config/academy_conversion/studies/<study-id>.json \
  --config <roster-source-config> \
  --run-dir <configured-run-dir> \
  --output-dir <configured-run-dir>/parsed-rosters
```

These stages fail if the supplied source config or run directory differs from
the frozen study, if its academy or roster seasons differ, or if an output
escapes the configured run directory.

Acquisition records distinguish transport, provider, target, content, cache,
and error-classification states. Completed records and permanent target/content
failures are reused without another request. Only transient transport failures,
HTTP 408/429, and 5xx target failures are eligible for a later bounded retry.

Roster candidates do not become denominator facts until a reviewed identity
table passes `resolve-rosters`. Worker alias proposals are merged only through
`merge-source-link-proposals`; the command fails closed on conflicting people
or source IDs and requires the exact compressed source-player table through
`--source-players`.

Analysis consumes four source-neutral CSVs documented in
`academy-conversion-data-contract.md`:

```bash
uv run academy-conversion analyze \
  --study-config config/academy_conversion/studies/<study-id>.json \
  --rosters <roster-memberships.csv> \
  --appearances <appearances.csv> \
  --competitions <competitions.csv> \
  --coverage <coverage.csv> \
  --output-dir <analysis-output>
```

The roster membership input must contain at least one reviewed membership for
every configured roster season, including the post-cohort boundary seasons.
Analysis stops before cohort construction when a configured season is absent;
otherwise a continuing youth player could be silently misclassified as an
exit.

Render the local report only from validated analysis artifacts:

```bash
uv run academy-conversion render-report \
  --study-config config/academy_conversion/studies/<study-id>.json \
  --summary <analysis-output>/cohort_summary.csv \
  --outcomes <analysis-output>/player_threshold_outcomes.csv \
  --appearances <facts>/appearances.csv \
  --competitions <facts>/competitions.csv
```

Every analysis run also emits `provenance.json`, containing the four input
artifact paths, roster/appearance/coverage source URLs, and competition-policy
versions used for the derived outcomes. It also records the exact study config
and normalized study summary. Cohort bounds, observation length, thresholds,
sustained-season count, competition policy, report identity, and report output
path come from that frozen config rather than parallel CLI flags.

## Editorial report contract

The public-facing report frames academy output through two simultaneous lenses:

- **production value:** confirmed senior opportunities, stable seasons,
  multi-season durability, and the highest competitive level reached;
- **career risk:** reaching the final youth squad does not guarantee a stable
  senior role, while incomplete evidence must remain unknown rather than being
  described as failure.

The editorial order is **claim -> evidence -> implication**. The public sample
is the study's configured exit cohort. Boundary-detection rosters, roster-season
row counts, report counts, and the larger identity universe are audit metadata,
not reader-facing findings, and stay out of the narrative.

Reader-facing copy uses football meanings such as “五大联赛”“职业联赛立足”和
“多赛季站稳”. Internal tier codes remain available in the embedded audit data
but are not required background knowledge. The main career chart crosses
competition level with one-season and multi-season durability rather than
mixing both dimensions into one funnel. The player table shows at most two real
competition names from qualifying seasons; names and country-level metadata
come from the versioned competition policy. The report distinguishes academy
production from Barcelona's own value capture: first-team minutes, transfer
revenue, first breakthrough club, and current club require separate datasets.

The static policy may mark a competition as career-eligible without modeling
historical status changes. Add validity fields only when a concrete season
change affects the observed sample. The current prototype source mainly covers
top divisions, so its “professional league” result remains a lower bound and
must not be described as complete coverage of leagues such as the Championship
or Serie C.

## Barcelona v1 audit snapshot

On 2026-08-27, seven official annual reports produced 163 visually reviewed
roster-season listings, 123 unique people, and 85 players whose final Juvenil A
roster season was 2015-16 through 2019-20. The adult-career prototype linked 76
of 123 roster identities and retained 47 as unresolved.

The limited adult dataset has zero completely covered players. At the primary
15-appearance threshold it observes 25 established players (29.4% of all 85)
and 14 sustained players (16.5%). These are conservative lower bounds only.
The 10/15/20 established lower bounds are 32.9%, 29.4%, and 22.4%; the sustained
lower bounds are 21.2%, 16.5%, and 14.1%.

## Claim boundary

- An observed positive is a data fact under the declared competition policy.
- A percentage with incomplete coverage is a lower-bound metric result.
- An unknown is not a negative.
- Cohort differences are descriptive and especially unstable at 12-21 players
  per cohort.
- This design does not estimate the causal effect of La Masia.
- A complete estimate requires a licensed or otherwise approved adult-career
  source covering every declared T0/T1/T2 competition and all 425 player-season
  windows.
