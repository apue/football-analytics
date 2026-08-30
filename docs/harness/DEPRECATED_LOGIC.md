# Deprecated logic

The replacement branch intentionally does not carry these PR #8 paths:

- combined `academy-conversion health`, `manifest`, `acquire`, and
  `validate-run` commands;
- Firecrawl scrape/batch-scrape state machine;
- direct HTTP-file provider and generic provider envelope;
- compatibility overrides for frozen study paths;
- supervisor/worker shard protocol in the academy skill.

They have no callers on `origin/main`. Their replacement is the narrow
`evidence-search` artifact contract and offline academy commands, so no
compatibility or migration layer is required.
