# PROBLEM_REVIEW

Status: resolved

## Symptom

Initial direct and worker PDF downloads were accepted despite truncation, and
the first identity pass treated Juan Brandariz Movilla `Chumi` and Juan
Brandáriz as different players.

## Evidence

- Official PDFs must end with `%%EOF`; truncated copies did not.
- Visual roster checks and an independent extraction agreed on 163 listings.
- Cross-season alias review showed the two Chumi rows refer to one person.

## Triage Class

Contract-mismatch.

## Root Cause Hypothesis

The first file contract checked only MIME, magic bytes, and size, so a partial
PDF could pass. Name normalization alone cannot resolve nickname and accent
variants across seasons.

## Impact Scope

- Affected stages: official report acquisition and roster identity resolution.
- Analytical impact: a false extra player and potentially incorrect exit year.
- No source or user data was overwritten; failed attempts remain diagnostic.

## Fix Options

1. Require a tail marker for formats that expose one; preserve every attempt.
2. Keep identity review separate from parsing and require evidence for aliases.

## Recommended Repair Depth

Contract repair.

## Validation Required

- Contract and regression tests for file validation and identity resolution.
- Seven complete PDFs, expected page counts, 163 candidate rows, 123 unique
  people, and 85 target exit-cohort players.

## Remaining Delta

- Adult-career coverage remains incomplete; the local result is a lower-bound
  prototype, not a complete conversion-rate estimate.
