# VALIDATION_PLAN

Status: accepted

## Validation Mode

Selected modes: contract-test, schema-check, regression-test, trace-review,
smoke-test, and screenshot-review.

Reason: the highest risks are external response contracts, deterministic
parsing and classification, resumable orchestration, worker policy adherence,
and final visual interpretation.

## Commands

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run --with pyyaml python \
  /Users/yangtian/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .codex/skills/academy-conversion-research
uv run academy-conversion validate-run \
  --study-config <fixture-study.json> \
  --run-dir <fixture-run>
```

The report is self-contained HTML and is checked through a local HTTP server
with `agent-browser` at desktop and mobile viewport sizes.

## Pass Criteria

- No test, lint, format, or lock failures.
- Outer-success/source-405 fixture is rejected.
- Golden roster and player-season fixtures parse as expected.
- Repeated acquisition is idempotent and resumable.
- Missing coverage remains unknown.
- Skill forward test changes only its temporary shard and returns a valid
  handoff.
- Final report numbers reconcile to exported artifacts.

## Manual Checks

- [x] Source terms and attribution recorded before bulk acquisition.
- [x] Every official roster page visually compared with its source.
- [x] Representative positive careers reconcile to appearance source facts.
- [x] Worker traces contain no secrets or unauthorized retries.
- [x] Report limitations use the evidence ladder.

## Known Gaps

- Automated Transfermarkt collection is prohibited without written permission.
- The prototype adult-career package has partial competition and identity
  coverage, so only positive observations and lower bounds are valid.
