# Architecture

```text
Firecrawl API -> search -> raw response -> normalized evidence.jsonl
                                                   |
                                                   v
approved academy sources -> parsed facts -> deterministic analysis -> report
```

## Boundaries

- `evidence_search`: Firecrawl v2 search request, response validation, URL
  canonicalization, domain/type/URL-term filtering, and auditable bundle
  persistence.
- `evidence_search_cli`: the single online command surface.
- `academy_roster_parser`: reviewed local-PDF parsing and roster validation.
- `academy_analysis`: validated input orchestration and analysis persistence.
- `academy_conversion`: pure identity, cohort, outcome, and summary rules.
- `academy_conversion_cli`: thin offline command and exit-code routing.
- Academy modules consume the provider-independent evidence contract and must
  not import `evidence_search` transport classes.
- `.codex/skills/firecrawl-evidence-search`: provider-specific operating
  guidance.
- `.codex/skills/academy-conversion-research`: domain guidance and routing to
  an evidence bundle when source discovery is needed.

## Evidence contract

`evidence.jsonl` contains one row per canonical URL with schema version,
query IDs, provider, URL, title, description, decision, rejection reasons, and
retrieval timestamp. `request.json` preserves the provider request contract,
while `raw/<query-id>.json` preserves each provider response;
`validation.json` summarizes accepted/rejected counts.

The filesystem is the handoff. A skill does not call another skill as a Python
function, and academy analysis does not depend on provider runtime state.
Every executable study freezes an approved evidence-bundle path; roster parsing
and analysis both fail before reading facts if any approved source URL is
missing from that bundle.
