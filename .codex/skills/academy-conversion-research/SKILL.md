---
name: academy-conversion-research
description: Run repeatable academy-to-senior conversion studies from an exact oldest-youth squad and exit interval using approved evidence, reviewed identities, deterministic career facts, and an evidence-limited report. Do not use for match-event analysis or causal academy claims.
---

# Academy Conversion Research

The learner defines the academy question and interpretation. Use code for
identity-safe joins, season windows, competition eligibility, thresholds,
aggregation, and percentages.

## Freeze the study

Require the exact oldest-youth squad and final-roster-season interval. Start
from [study-config.template.json](assets/study-config.template.json). Unless the
learner changes them explicitly, observe the next five complete seasons, use 15
eligible domestic senior-league appearances for one-season establishment, two
qualifying seasons for sustained establishment, and report 10/15/20 sensitivity.
Encode `2018-19` as season start `2018` and treat both interval endpoints as
inclusive. The roster window must include at least one season after the final
requested exit season; otherwise the last observed roster season is not proven.

Read [research-contract.md](references/research-contract.md) before changing
definitions or interpreting results.

## Evidence boundary

If official source URLs are not frozen, use the repository's
`firecrawl-evidence-search` skill to create `evidence.jsonl`. The handoff is the
artifact, not a runtime skill call. Review candidate authority, then freeze the
approved URLs in the academy source config. That config is the review artifact:
each page records its canonical URL, roster season/page, local filename,
expected player count, and confirmed visual-review status. Do not mark the
source policy approved when no page has an accepted evidence row.

Validate discovery coverage with:

```bash
uv run academy-conversion validate-sources \
  --source-config <academy-sources.json> \
  --evidence <evidence.jsonl>
```

The academy code must not read provider credentials or Firecrawl transport
responses.

## Deterministic research

Place reviewed PDFs under an ignored local directory and create candidates with:

```bash
uv run --with pymupdf academy-conversion parse-official-rosters \
  --study-config <study.json> \
  --pdf-dir <reviewed-pdfs> \
  --output-dir <configured-run-dir>/parsed-rosters
```

The parser records season, source URL/page, local content hash, and expected
count validation. Resolve its candidates to stable player IDs only from
reviewed identity evidence. Never guess identities or turn missing career
coverage into zero appearances. Before analysis, freeze the adult-source scope
and competition policy, including which domestic senior leagues are eligible
and the coverage status for every player-season. Then run:

```bash
uv run academy-conversion analyze \
  --study-config <study.json> \
  --rosters <roster-memberships.csv> \
  --appearances <appearances.csv> \
  --competitions <competitions.csv> \
  --coverage <coverage.csv> \
  --output-dir <configured-run-dir>/analysis
```

Render only after `validation.json` passes. Use `verify-baseline` when migrating
an established study. Report source coverage, unknown outcomes, source-set
differences, checks, branch, and commit.

Stop when the exit interval or season encoding is unclear, the roster window is
too short to establish final seasons, no official source is approved, an
approved URL lacks accepted evidence, roster provenance is missing, identities
remain unresolved, the adult scope or competition policy is not frozen,
competition facts do not match that policy, or coverage cannot distinguish
absence from missing observation. Incomplete career coverage supports only
conservative lower-bound claims.
