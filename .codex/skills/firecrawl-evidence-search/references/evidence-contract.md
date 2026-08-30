# Evidence bundle contract

Each `evidence.jsonl` row has schema version `1` and these fields:

- provider, original URL, canonical URL, and retrieval timestamp;
- all query IDs that returned the canonical URL;
- title, description, and provider category when present;
- `accepted` or `rejected` decision and mechanical rejection reasons.

Accepted means only that the URL passed the configured domain, PDF, and required
URL-term gates. It does not establish source authority, factual accuracy,
completeness, or reuse permission.

An online run directory contains:

```text
request.json
raw/<query-id>.json
evidence.jsonl
validation.json
```

Raw responses may change across runs. Replayed fixtures and normalized bundle
generation are deterministic when the retrieval timestamp is fixed.
Replay requires query IDs/text, result limit, and country to match
`request.json`; deterministic domain and required-URL-term filters may be
changed and audited without another provider call. The PDF setting is part of
the provider request and must also match.
