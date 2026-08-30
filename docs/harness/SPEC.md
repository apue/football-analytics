# Academy evidence research replacement

## Goal

Replace PR #8 with a reusable academy-conversion research workflow whose web
discovery is a separate KeyPool-routed Firecrawl search capability.

## Requirements

- `evidence-search` searches through KeyPool, preserves the raw provider
  response, normalizes and filters candidates, and writes `evidence.jsonl`.
- `academy-conversion` contains no KeyPool or Firecrawl knowledge. It consumes
  approved evidence records and deterministic roster/career facts.
- The Barcelona Juvenil A 2015-16 through 2019-20 study reproduces the frozen
  source set and the current conservative lower-bound analysis.
- Credentials come from environment variables or an explicitly supplied env
  file and are never stored in artifacts or logs.

## Strong constraints

- No backward compatibility with PR #8 command or artifact shapes.
- Delete obsolete combined acquisition paths instead of wrapping them.
- Add only abstractions and configuration required by this study and a second
  academy using the same evidence contract.
- Keep provider transport, evidence selection, academy definitions, analysis,
  and rendering in separate modules.

## Non-goals

- General-purpose crawling or scraping.
- A provider plug-in framework.
- Automated identity decisions.
- Causal claims about academy quality.
- Complete professional-career coverage; the current public adult source is a
  partial dataset, so results remain conservative lower bounds.
