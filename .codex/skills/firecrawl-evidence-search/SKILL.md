---
name: firecrawl-evidence-search
description: Discover and mechanically filter auditable web-source candidates through the direct Firecrawl API. Use when research needs candidate URLs or a reproducible evidence bundle. Do not use to analyze domain facts or download a known URL.
---

# Firecrawl Evidence Search

Produce a provider-independent evidence bundle. Search results are candidates,
not approved facts; downstream research owns source interpretation.

## Inputs

Require a version-one search config containing explicit queries, allowed
domains, required URL terms, result limit, country, and whether results must be
PDFs. Create a committed config only when those choices are part of a
repeatable study.

Load `FIRECRAWL_API_KEY` from the process environment. Never print or persist
its value.

## Run

```bash
uv run evidence-search \
  --config <search-config.json> \
  --output-dir data/processed/evidence-search/<run-id>
```

The command calls Firecrawl v2 search directly, preserves each raw
response, canonicalizes and deduplicates URLs, applies only the configured
domain/PDF/required-URL-term filters, and writes `evidence.jsonl` plus
`validation.json`.
Use `--replay-raw-dir <previous-run>/raw` to rebuild a bundle offline after
changing deterministic filters; replay does not require credentials.

Read [evidence-contract.md](references/evidence-contract.md) before changing or
consuming the artifact shape.

## Review and handoff

- Inspect rejected reasons and accepted canonical URLs.
- Treat ranking, snippets, and live recall as volatile.
- Compare a live run by canonical URL set; do not require result-order equality.
- Return the config path, output directory, validation summary, and source-set
  differences. Do not paraphrase raw evidence as the handoff.

Stop if source policy is unresolved, the provider response fails validation,
the bundle is empty or has no accepted candidates, the query would bypass
access controls, or accepted sources need domain judgment.
This skill intentionally has no scrape, crawl, batch, provider plug-in, retry,
or compatibility workflow.
