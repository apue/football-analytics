# Academy conversion source policy

Status: approved for FC Barcelona annual reports; prohibited for automated
Transfermarkt collection without written permission.

Reviewed: 2026-08-27

## FC Barcelona annual reports

The club's official annual-report archive is the primary source for historical
Juvenil A season rosters:

- Archive: https://www.fcbarcelona.com/en/club/organisation-and-strategic-plan/commissions-and-bodies/annual-reports
- Intended use: download the official 2015-16 through 2021-22 reports, preserve
  URL and SHA-256, and extract the `JUVENIL A` / `PLANTILLA` section.
- Acquisition: direct public PDF download with low concurrency and local cache.
- Publication: publish derived roster facts with source attribution and links;
  do not redistribute the source PDFs.

The relevant roster page in every report must be visually checked. Text
extraction alone does not establish that the table is complete.

## Transfermarkt

Transfermarkt Terms of Use section 11.1 prohibits bots, spiders, screen
scraping, and other automated processes that access or copy digital content:

- Terms: https://www.transfermarkt.com/intern/anb#11-copyright-rights-of-use
- Legal notice: https://www.transfermarkt.com/intern/

The academy pipeline must not use Firecrawl, agent-browser, or another automated
provider for systematic Transfermarkt collection without written permission.
Previously collected single-page feasibility observations are not an approved
bulk source and must not become production fixtures or published data.

## Public derivative datasets

`dcaribou/transfermarkt-datasets` publishes its derivative package as CC0, but
its current competition coverage is limited and the CC0 declaration does not
resolve rights in the original source. It may be used only as an explicitly
limited technical prototype after a run records that limitation; absence of an
appearance row cannot be interpreted as zero.

- Project: https://github.com/dcaribou/transfermarkt-datasets
- Dataset: https://www.kaggle.com/datasets/davidcariboo/player-scores

No free source with clear reuse terms and complete global T1/T2 coverage was
identified in the 2026-08-27 audit. Full adult-career research therefore
requires a licensed source, a documented set of official-league sources, or a
narrower competition scope.
