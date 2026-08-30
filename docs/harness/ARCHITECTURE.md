# Architecture

```text
KeyPool -> Firecrawl search -> raw response -> normalized evidence.jsonl
                                                   |
                                                   v
approved academy sources -> parsed facts -> deterministic analysis -> report
```

## Boundaries

- `evidence_search`: Firecrawl v2 search request, response validation, URL
  canonicalization, domain/type/URL-term filtering, and auditable bundle
  persistence.
- `evidence_search_cli`: the single online command surface.
- `academy_*`: academy study contract, roster/career facts, validation,
  analysis, and report rendering. These modules must not import
  `evidence_search` transport classes.
- `academy_conversion_cli`: offline academy commands plus validation that an
  approved source set is represented in an evidence bundle.
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
