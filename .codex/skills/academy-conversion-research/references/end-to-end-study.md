# End-to-end academy study

Use this procedure when the user names an academy squad and a cohort interval
and expects the complete research output.

## 1. Freeze the request

Create a study ID from the academy, squad, and inclusive exit interval, for
example `real-madrid-u19-2015-2019`. Copy the study-config asset into
`config/academy_conversion/studies/<study-id>.json` and replace every placeholder.

Confirm from the completed file:

- squad identity and denominator definition;
- roster seasons used to detect the final listed season;
- inclusive target exit seasons and five following observation seasons;
- 10/15/20 appearance thresholds, with 15 primary;
- professional-league and achievement-level policy;
- roster and adult-career sources, their adapters, and policy status;
- local run directory and report path.

Treat a year pair such as `2015-2020` as ambiguous until it is normalized to
season starts or explicit season labels. Preserve the user's intended inclusive
cohort count in the study file.

Run the skill's `validate_study_config.py` after completing the file. Before
live acquisition, rerun it with `--require-approved`; both source policy states
must be approved.

## 2. Onboard sources

Read `docs/sources/academy-conversion.md` and the provider-policy reference.
Record approval separately for the academy roster source and adult-career
source. Run the acquisition health and target-content gate before bulk work.

For a new academy, inspect one representative roster season manually. Reuse an
existing parser only when the page markers, squad boundary, row structure, and
golden fixture match. Otherwise enter source-adapter mode and add a focused
adapter with tests before acquiring the full interval.

The roster interval must extend beyond the final target season far enough to
avoid treating a continuing youth player as an exit. Record the actual boundary
seasons in the study config rather than relying on a universal offset.

## 3. Build validated facts

Follow the repository stage order:

```text
configured -> manifested -> acquired -> parsed -> identity-reviewed
-> career-facts -> validated -> analyzed -> rendered
```

Use `uv run academy-conversion --help` as the live command inventory. The usual
commands are `health`, `manifest`, `acquire`, `validate-run`, roster parsing,
`resolve-rosters`, an approved adult-source adapter, `analyze`, and
`render-report`.

Persist source evidence and machine-readable coverage. Missing player-season
facts remain unknown. The supervisor reviews identity conflicts and merges only
confirmed mappings. Workers, when used, receive immutable disjoint shards and
write only their shard directories.

## 4. Analyze

Code owns the final-roster cohort assignment, five-season windows, league
eligibility, appearance aggregation, thresholds, durability, percentages, and
sensitivity analysis. One player counts once in each nested outcome. Do not add
appearances across different analytical competition levels to cross a threshold.

The professional-career dimension and competitive-height dimension are
separate:

- professional establishment: at least 15 appearances in one eligible adult
  professional-league season;
- sustained professional establishment: the same in at least two seasons;
- competitive height: highest eligible reporting band reached under the same
  appearance rule.

Reserve or B-team identity does not matter when the team competes in an eligible
adult professional league. Cups, youth leagues, and pure reserve competitions
outside the adult pyramid do not count.

## 5. Render and verify

Read the report-contract reference, then render from validated summary,
outcome, appearance, roster, and competition-policy artifacts. Regenerating a
report from unchanged facts does not require reacquisition.

Verify at minimum:

- displayed sample size equals the target exit cohort;
- every chart numerator reconciles to player outcomes;
- the player table contains the same players exactly once;
- representative leagues come only from qualifying seasons and list at most two;
- unknown coverage is not displayed as failure;
- the report states whether percentages are complete estimates or lower bounds;
- focused tests, repository checks, and report-script syntax pass.

Use the repository checkpoint skill after modifications. Hosting remains a
separate action requiring explicit confirmation.

## 6. Handoff

Return the local report link first, followed by the study ID, denominator,
headline results, coverage state, important source limitations, branch, commit,
verification, and remote status. If source policy or coverage blocks a complete
result, deliver validated intermediate artifacts and name the exact blocker
rather than substituting a convenient source.
