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

Official roster reports use
`config/academy_conversion/barcelona_juvenil_a_rosters.json`. Generate and
acquire its manifest, require `validate-run` to pass, then parse with:

```bash
uv run --with pymupdf academy-conversion parse-official-rosters \
  --config config/academy_conversion/barcelona_juvenil_a_rosters.json \
  --run-dir <official-source-run> \
  --output-dir <parsed-output>
```

Roster candidates do not become denominator facts until a reviewed identity
table passes `resolve-rosters`. Worker alias proposals are merged only through
`merge-source-link-proposals`; the command fails closed on conflicting people
or source IDs and requires the exact compressed source-player table through
`--source-players`.

Analysis consumes four source-neutral CSVs documented in
`academy-conversion-data-contract.md`:

```bash
uv run academy-conversion analyze \
  --rosters <roster-memberships.csv> \
  --appearances <appearances.csv> \
  --competitions <competitions.csv> \
  --coverage <coverage.csv> \
  --output-dir <analysis-output> \
  --exit-start 2015 --exit-end 2019 --thresholds 10,15,20
```

Render the local report only from validated analysis artifacts:

```bash
uv run academy-conversion render-report \
  --summary <analysis-output>/cohort_summary.csv \
  --outcomes <analysis-output>/player_threshold_outcomes.csv \
  --rosters <roster-memberships.csv> \
  --appearances <facts>/appearances.csv \
  --competition-policy config/academy_conversion/competition_policy_prototype_v1.json \
  --output <run>/report/index.html \
  --primary-threshold 15
```

Every analysis run also emits `provenance.json`, containing the four input
artifact paths, roster/appearance/coverage source URLs, and competition-policy
versions used for the derived outcomes.

## Editorial report contract

The public-facing report frames academy output through two simultaneous lenses:

- **production value:** confirmed senior opportunities, stable seasons,
  multi-season durability, and the highest competitive level reached;
- **career risk:** reaching the final youth squad does not guarantee a stable
  senior role, while incomplete evidence must remain unknown rather than being
  described as failure.

The editorial order is **claim -> evidence -> implication**. The public sample
is the 85 target exit-cohort players. Boundary-detection rosters, roster-season
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
