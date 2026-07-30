---
name: select-match-data
description: Resolve football competitions, seasons, teams, managers, and matches against the local StatsBomb open-data catalog; inspect coverage; and fetch confirmed event, lineup, or 360 files. Use when the learner asks to find, choose, compare, or download football data, including requests expressed with aliases, misspellings, latest-season language, or several filters.
---

# Select Match Data

Use the catalog as the deterministic interface. Use reasoning to translate the
football request into filters and to judge whether the available sample can
answer it. Do not recreate catalog parsing, fuzzy matching, sync, or download
logic in ad hoc Python or SQL.

## Select a reproducible scope

1. Separate the requested **data scope** from the **analysis question**.
   "Real Madrid's performance" still needs a football behavior, outcome,
   comparison baseline, and context before analysis begins.
2. Resolve every named competition, team, or manager:

   ```bash
   uv run catalog resolve competition "<name>"
   uv run catalog resolve team "<name>"
   uv run catalog resolve manager "<name>"
   ```

   Use an exact resolved ID directly. For `resolution_required`, show the
   candidates and wait for learner confirmation; never silently choose the top
   fuzzy result. For `not_found`, retry once with a likely provider-language
   translation, transliteration, or shorter canonical fragment. Show that
   semantic mapping before using it; do not grow the alias file for every
   one-off translation.
3. Prefer structured catalog commands:

   ```bash
   uv run catalog seasons --competition-id <id> --team-id <id> --limit 5
   uv run catalog matches --competition-id <id> --season-id <id> --team-id <id>
   ```

   Add `--manager-id`, `--has-360`, `--date-from`, or `--date-to` when the
   question requires them. When both manager and team IDs are present, the
   catalog requires that manager to have coached that team in the match.
4. Interpret "latest" as the eligible row with the latest
   `last_match_date` after applying competition and team filters. Do not sort
   opaque season IDs or season-name strings.
5. Report `available_match_count`, event/lineup/360 counts, date range, catalog
   freshness, and `source_commit`. Open-data presence does not prove a complete
   competition season. Describe an incomplete sample as "available matches,"
   not as season performance.
6. Ask the learner to confirm any ambiguous entity, incomplete sample, or
   materially different scope. If coverage is inadequate, offer to narrow the
   claim, choose another season, or use another data source.
7. After scope confirmation, fetch only the selected IDs:

   ```bash
   uv run catalog fetch --match-id <id> --match-id <id>
   ```

   Record the query, match count, limitations, and source commit in the active
   lesson's `brief.md` or `checks.md` when the selection becomes lesson scope.

## Handle long-tail queries

Use read-only SQL only when the structured commands cannot express the
selection. Query the documented views:

- `catalog_competition_seasons`
- `catalog_team_seasons`
- `catalog_matches`
- `catalog_match_managers`

Run one `SELECT` or `WITH` statement through:

```bash
uv run catalog sql "<statement>"
```

Preview the returned scope and coverage before fetching. If the same query
shape recurs, improve the catalog interface instead of accumulating SQL in
this Skill.

## Preserve analysis boundaries

- Do not refresh the catalog from a Notebook. Catalog commands own the
  seven-day freshness check.
- Do not fetch match files until entity and scope decisions are resolved.
- Do not treat catalog counts as football findings.
- Do not update the lesson handoff for an exploratory query that changed no
  learning decision.
