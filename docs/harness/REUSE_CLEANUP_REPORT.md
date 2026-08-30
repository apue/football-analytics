# Reuse and cleanup report

## Evidence inspected

- `git diff --name-status origin/main...research/la-masia-conversion`
- definitions and tests in PR #8 academy and acquisition modules
- the frozen Barcelona study/config and ignored run outputs
- current Firecrawl v2 search documentation

## Decision

- Reuse domain formulas and verified Barcelona fixtures.
- Refactor the academy CLI around offline domain stages.
- Implement a new narrow Firecrawl search module.
- Delete rather than migrate the combined provider lifecycle and CLI paths.
- Validate exact deterministic replay offline and canonical source coverage
  online; do not require volatile search order equality.

## Risks

- Search indexes can omit old PDFs or return redirect variants; canonical URL
  comparison and explicit diff reporting are required.
- Adult career coverage is partial, so negative outcomes remain unknown rather
  than confirmed failures.
