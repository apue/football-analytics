# Acceptance

## Offline gates

- Firecrawl requests use the direct `https://api.firecrawl.dev/v2/search`
  endpoint and bearer auth without exposing the key.
- Provider failures and malformed response shapes fail closed.
- Canonicalization, deduplication, allowed-domain filtering, PDF filtering,
  deterministic ordering, and bundle validation have contract tests.
- Academy modules do not import Firecrawl transport code.
- A complete frozen official-source set validates against an accepted evidence
  bundle; incomplete live recall fails closed and reports exact differences.
- The committed minimal Barcelona roster/career fixtures reproduce 85
  exit-cohort players, zero validation issues, and the frozen cohort summary
  from a fresh checkout.
- Skill packages pass `quick_validate.py`.

## Online gate

Run the committed Barcelona query through the direct Firecrawl API. Preserve
the raw response and compare canonical accepted URLs to the frozen source set.
Search ordering may change; every difference must be reported, while the
source-set validation and downstream analysis must remain reproducible from
frozen input.
Also compare normalized candidates, excluding only retrieval time, with the
last accepted online result so filter drift is explicit.

## Delivery gate

Full tests, Ruff, lock check, diff check, CI, Standards review, and Spec review
pass. Review findings are fixed and reverified. The replacement PR is not
merged without explicit user confirmation.
