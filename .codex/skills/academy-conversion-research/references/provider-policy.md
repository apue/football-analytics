# Provider and source policy

Before bulk acquisition, record the source owner and page type, terms review
date, robots or rate-limit constraints, allowed provider and concurrency,
attribution and redistribution boundary, and any allowed fallback.

The repository decision record is `docs/sources/academy-conversion.md`. FC
Barcelona official annual-report PDFs are approved for the roster denominator.
Automated Transfermarkt collection is prohibited without written permission.

## Firecrawl target gate

Validate all of the following separately:

1. KeyPool configuration loads without exposing secrets.
2. Firecrawl returns a JSON object with outer success.
3. Target metadata status is 2xx.
4. Required page markers and minimum structural counts are present.
5. The page parser matches a manually verified golden fixture.

An outer success with target status 405 is a failure. Do not start batch scrape
until representative roster and player-season pages pass.

## Retry policy

- Retry bounded timeouts, 429, and 5xx responses with backoff.
- Do not retry authentication failures, target 401/403/405, policy blocks, or
  content-contract failures without supervisor review.
- Never switch to an enhanced proxy solely to evade a source restriction.
