# Decisions

## Accepted

- Branch from current `origin/main`; keep PR #8 unchanged as a comparison
  baseline until the replacement is reviewed.
- Use a file artifact contract rather than runtime skill-to-skill invocation.
- Keep one provider-specific implementation: KeyPool-routed Firecrawl v2
  search. Do not build a provider abstraction without a second provider.
- Treat raw search ranking as volatile. Exact equality is required for replayed
  fixtures and downstream analysis, not live ranking.
- Preserve the current five-season window, 15-appearance primary threshold,
  two-season sustained threshold, and 10/15/20 sensitivity thresholds.

## Rejected

- Cherry-picking the combined PR #8 pipeline wholesale.
- Compatibility aliases for old CLI commands or artifact layouts.
- Retaining batch scrape, direct HTTP download, cache/resume state machines,
  supervisor/worker sharding, or generic provider envelopes without a current
  acceptance requirement.
