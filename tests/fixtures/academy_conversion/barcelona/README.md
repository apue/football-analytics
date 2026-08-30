# Barcelona baseline fixture

These four normalized CSVs are the smallest complete input set needed to
reproduce the frozen 85-player Barcelona Juvenil A analysis in CI.

- `roster_memberships.csv` derives from the visually reviewed FC Barcelona
  annual-report pages recorded in
  `config/academy_conversion/barcelona_juvenil_a_rosters.json`.
- `appearances.csv`, `competitions.csv`, and `coverage.csv` are the reviewed
  partial-scope facts retained from PR #8's local
  `dcaribou/transfermarkt-datasets` feasibility snapshot.

The fixture contains normalized research facts only: no source PDFs, raw
provider payloads, cache state, compatibility artifacts, or unpublished
identity-review evidence. It is a regression fixture, not a claim of complete
professional-career coverage.
