"""Source-neutral academy-to-senior conversion calculations."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RosterMembership:
    """One player listed in one academy roster season."""

    player_id: str
    player_name: str
    academy_id: str
    season_start: int
    source_url: str


@dataclass(frozen=True)
class RosterCandidate:
    """One displayed roster name extracted from source evidence."""

    candidate_id: str
    displayed_name: str
    academy_id: str
    season_start: int
    source_url: str
    source_page: int
    position: str = ""


@dataclass(frozen=True)
class IdentityResolution:
    """A reviewed link from one source candidate to a stable player ID."""

    candidate_id: str
    player_id: str
    status: str
    evidence: str


@dataclass(frozen=True)
class ExitCohort:
    """A unique academy player assigned to their final roster season."""

    player_id: str
    player_name: str
    academy_id: str
    exit_season_start: int
    roster_season_count: int


@dataclass(frozen=True)
class AppearanceRow:
    """Observed appearances in one player-club-competition season."""

    player_id: str
    season_start: int
    club_id: str
    competition_id: str
    appearances: int
    source_url: str


@dataclass(frozen=True)
class CompetitionRule:
    """Versionable classification for one competition season."""

    competition_id: str
    season_start: int
    tier: str
    tier_rank: int
    eligible_domestic_league: bool
    policy_version: str = "v1"


@dataclass(frozen=True)
class CoverageRow:
    """Coverage status for one player observation season."""

    player_id: str
    season_start: int
    status: str
    scope_id: str = "declared"
    source_url: str = ""


@dataclass(frozen=True)
class PlayerOutcome:
    """Derived conversion outcomes for one academy exit."""

    player_id: str
    player_name: str
    exit_season_start: int
    highest_reached_tier: str | None
    established_tiers: Mapping[int, str | None]
    sustained_tiers: Mapping[int, str | None]
    threshold_status: Mapping[int, str]
    sustained_status: Mapping[int, str]
    coverage_complete: bool


@dataclass(frozen=True)
class ValidationIssue:
    """One deterministic reason that source facts are not analysis-ready."""

    code: str
    row_type: str
    key: str
    detail: str


def resolve_roster_memberships(
    candidates: Iterable[RosterCandidate],
    resolutions: Iterable[IdentityResolution],
) -> tuple[list[RosterMembership], list[ValidationIssue]]:
    """Promote only uniquely confirmed identities into analytical rosters."""

    resolution_groups: dict[str, list[IdentityResolution]] = defaultdict(list)
    for resolution in resolutions:
        resolution_groups[resolution.candidate_id].append(resolution)

    memberships: list[RosterMembership] = []
    issues: list[ValidationIssue] = []
    for candidate in candidates:
        candidate_resolutions = resolution_groups.get(candidate.candidate_id, [])
        if len(candidate_resolutions) != 1:
            issues.append(
                ValidationIssue(
                    "missing_or_duplicate_identity_resolution",
                    "roster_candidate",
                    candidate.candidate_id,
                    f"resolution_rows={len(candidate_resolutions)}",
                )
            )
            continue
        resolution = candidate_resolutions[0]
        if resolution.status != "confirmed" or not resolution.player_id:
            issues.append(
                ValidationIssue(
                    "unresolved_roster_identity",
                    "roster_candidate",
                    candidate.candidate_id,
                    f"status={resolution.status}",
                )
            )
            continue
        memberships.append(
            RosterMembership(
                resolution.player_id,
                candidate.displayed_name,
                candidate.academy_id,
                candidate.season_start,
                candidate.source_url,
            )
        )
    return (
        sorted(memberships, key=lambda row: (row.season_start, row.player_id)),
        sorted(issues, key=lambda issue: (issue.code, issue.key)),
    )


def validate_research_rows(
    memberships: Iterable[RosterMembership],
    appearances: Iterable[AppearanceRow],
    rules: Iterable[CompetitionRule],
    coverage: Iterable[CoverageRow],
) -> list[ValidationIssue]:
    """Validate source-neutral rows without treating missing facts as zero."""

    membership_rows = list(memberships)
    appearance_rows = list(appearances)
    rule_rows = list(rules)
    coverage_rows = list(coverage)
    issues: list[ValidationIssue] = []
    roster_player_ids = {row.player_id for row in membership_rows}

    roster_keys = [
        (row.academy_id, row.season_start, row.player_id) for row in membership_rows
    ]
    for key, count in Counter(roster_keys).items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    "duplicate_roster_membership",
                    "roster_membership",
                    "|".join(map(str, key)),
                    f"rows={count}",
                )
            )

    appearance_keys = [
        (row.player_id, row.season_start, row.club_id, row.competition_id)
        for row in appearance_rows
    ]
    for key, count in Counter(appearance_keys).items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    "duplicate_appearance_fact",
                    "appearance",
                    "|".join(map(str, key)),
                    f"rows={count}",
                )
            )
    for row in appearance_rows:
        if row.player_id not in roster_player_ids:
            issues.append(
                ValidationIssue(
                    "appearance_player_not_in_roster",
                    "appearance",
                    row.player_id,
                    "player has no roster membership",
                )
            )
        if row.appearances < 0:
            issues.append(
                ValidationIssue(
                    "negative_appearances",
                    "appearance",
                    f"{row.player_id}|{row.season_start}|{row.club_id}|{row.competition_id}",
                    f"appearances={row.appearances}",
                )
            )

    rule_keys = [(row.competition_id, row.season_start) for row in rule_rows]
    rule_key_set = set(rule_keys)
    missing_rule_keys = {
        (row.competition_id, row.season_start)
        for row in appearance_rows
        if (row.competition_id, row.season_start) not in rule_key_set
    }
    for key in sorted(missing_rule_keys):
        issues.append(
            ValidationIssue(
                "missing_competition_rule",
                "appearance",
                "|".join(map(str, key)),
                "appearance cannot be classified",
            )
        )

    for key, count in Counter(rule_keys).items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    "duplicate_competition_rule",
                    "competition_rule",
                    "|".join(map(str, key)),
                    f"rows={count}",
                )
            )

    allowed_coverage = {"complete", "partial", "missing"}
    coverage_keys = [(row.player_id, row.season_start) for row in coverage_rows]
    for key, count in Counter(coverage_keys).items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    "duplicate_coverage_row",
                    "coverage",
                    "|".join(map(str, key)),
                    f"rows={count}",
                )
            )
    for row in coverage_rows:
        coverage_key = f"{row.player_id}|{row.season_start}"
        if row.player_id not in roster_player_ids:
            issues.append(
                ValidationIssue(
                    "coverage_player_not_in_roster",
                    "coverage",
                    coverage_key,
                    "player has no roster membership",
                )
            )
        if row.status not in allowed_coverage:
            issues.append(
                ValidationIssue(
                    "invalid_coverage_status",
                    "coverage",
                    f"{row.player_id}|{row.season_start}",
                    f"status={row.status}",
                )
            )
        if not row.scope_id:
            issues.append(
                ValidationIssue(
                    "missing_coverage_scope",
                    "coverage",
                    coverage_key,
                    "scope_id is required",
                )
            )
        if not row.source_url:
            issues.append(
                ValidationIssue(
                    "missing_coverage_source",
                    "coverage",
                    coverage_key,
                    "source_url is required",
                )
            )
    return sorted(issues, key=lambda issue: (issue.code, issue.key))


def build_exit_cohorts(
    memberships: Iterable[RosterMembership], *, exit_start: int, exit_end: int
) -> list[ExitCohort]:
    """Assign each unique player to their final observed academy roster season."""

    by_player: dict[str, list[RosterMembership]] = defaultdict(list)
    for row in memberships:
        by_player[row.player_id].append(row)

    cohorts: list[ExitCohort] = []
    for rows in by_player.values():
        final = max(rows, key=lambda row: row.season_start)
        if exit_start <= final.season_start <= exit_end:
            cohorts.append(
                ExitCohort(
                    player_id=final.player_id,
                    player_name=final.player_name,
                    academy_id=final.academy_id,
                    exit_season_start=final.season_start,
                    roster_season_count=len({row.season_start for row in rows}),
                )
            )
    return sorted(cohorts, key=lambda row: (row.exit_season_start, row.player_id))


def observation_seasons(exit_season_start: int, count: int = 5) -> tuple[int, ...]:
    """Return complete seasons immediately following the academy exit season."""

    if count < 1:
        raise ValueError("observation season count must be positive")
    return tuple(range(exit_season_start + 1, exit_season_start + count + 1))


def calculate_player_outcomes(
    cohorts: Iterable[ExitCohort],
    appearances: Iterable[AppearanceRow],
    rules: Iterable[CompetitionRule],
    coverage: Iterable[CoverageRow],
    *,
    thresholds: tuple[int, ...] = (10, 15, 20),
    observation_season_count: int = 5,
    sustained_qualifying_seasons: int = 2,
) -> list[PlayerOutcome]:
    """Calculate reached, established, and sustained tiers per player."""

    if sustained_qualifying_seasons < 2:
        raise ValueError("sustained qualifying seasons must be at least two")
    if sustained_qualifying_seasons > observation_season_count:
        raise ValueError(
            "sustained qualifying seasons cannot exceed the observation window"
        )
    exact, _, labels, _ = aggregate_eligible_appearances(appearances, rules)

    coverage_index = {(row.player_id, row.season_start): row.status for row in coverage}
    results: list[PlayerOutcome] = []
    for cohort in cohorts:
        seasons = observation_seasons(
            cohort.exit_season_start, observation_season_count
        )
        player_exact = {
            key: value
            for key, value in exact.get(cohort.player_id, {}).items()
            if key[0] in seasons
        }
        reached_ranks = [rank for (_, rank), value in player_exact.items() if value > 0]
        highest_reached = (
            _tier_for_rank(min(reached_ranks), labels) if reached_ranks else None
        )

        established: dict[int, str | None] = {}
        sustained: dict[int, str | None] = {}
        statuses: dict[int, str] = {}
        sustained_statuses: dict[int, str] = {}
        coverage_complete = all(
            coverage_index.get((cohort.player_id, season)) == "complete"
            for season in seasons
        )
        for threshold in thresholds:
            qualifying = {
                (season, rank)
                for (season, rank), value in player_exact.items()
                if value >= threshold
            }
            if qualifying:
                best_rank = min(rank for _, rank in qualifying)
                established[threshold] = _tier_for_rank(best_rank, labels)
                statuses[threshold] = "reached"
            else:
                established[threshold] = None
                statuses[threshold] = "not_reached" if coverage_complete else "unknown"

            sustained_rank = None
            for candidate_rank in sorted(labels):
                qualifying_seasons = {
                    season for season, rank in qualifying if rank <= candidate_rank
                }
                if len(qualifying_seasons) >= sustained_qualifying_seasons:
                    sustained_rank = candidate_rank
                    break
            sustained[threshold] = (
                _tier_for_rank(sustained_rank, labels)
                if sustained_rank is not None
                else None
            )
            sustained_statuses[threshold] = (
                "reached"
                if sustained_rank is not None
                else "not_reached"
                if coverage_complete
                else "unknown"
            )

        results.append(
            PlayerOutcome(
                player_id=cohort.player_id,
                player_name=cohort.player_name,
                exit_season_start=cohort.exit_season_start,
                highest_reached_tier=highest_reached,
                established_tiers=established,
                sustained_tiers=sustained,
                threshold_status=statuses,
                sustained_status=sustained_statuses,
                coverage_complete=coverage_complete,
            )
        )
    return results


def aggregate_eligible_appearances(
    appearances: Iterable[AppearanceRow], rules: Iterable[CompetitionRule]
) -> tuple[
    dict[str, dict[tuple[int, int], int]],
    dict[tuple[str, int, str], int],
    dict[int, set[str]],
    dict[tuple[str, int], int],
]:
    """Aggregate eligible league appearances once for analysis and reporting."""

    rule_index = {
        (row.competition_id, row.season_start): row
        for row in rules
        if row.eligible_domestic_league
    }
    by_level: dict[str, dict[tuple[int, int], int]] = defaultdict(
        lambda: defaultdict(int)
    )
    by_competition: dict[tuple[str, int, str], int] = defaultdict(int)
    labels: dict[int, set[str]] = defaultdict(set)
    ranks: dict[tuple[str, int], int] = {}
    for row in appearances:
        rule = rule_index.get((row.competition_id, row.season_start))
        if rule is None or row.appearances <= 0:
            continue
        by_level[row.player_id][(row.season_start, rule.tier_rank)] += row.appearances
        by_competition[(row.player_id, row.season_start, row.competition_id)] += (
            row.appearances
        )
        labels[rule.tier_rank].add(rule.tier)
        ranks[(row.competition_id, row.season_start)] = rule.tier_rank
    return (
        {player: dict(values) for player, values in by_level.items()},
        dict(by_competition),
        {rank: set(values) for rank, values in labels.items()},
        ranks,
    )


def select_representative_competitions(
    exit_seasons: Mapping[str, int],
    appearances: Iterable[AppearanceRow],
    rules: Iterable[CompetitionRule],
    *,
    threshold: int,
    observation_season_count: int = 5,
    limit: int = 2,
) -> dict[str, tuple[str, ...]]:
    """Select up to ``limit`` competitions involved in qualifying seasons."""

    if threshold < 1:
        raise ValueError("threshold must be positive")
    if limit < 1:
        raise ValueError("representative competition limit must be positive")
    by_level, by_competition, _, ranks = aggregate_eligible_appearances(
        appearances, rules
    )
    selected: dict[str, tuple[str, ...]] = {}
    for player_id, exit_season in exit_seasons.items():
        seasons = set(observation_seasons(exit_season, observation_season_count))
        qualifying = {
            (season, rank)
            for (season, rank), count in by_level.get(player_id, {}).items()
            if season in seasons and count >= threshold
        }
        candidates: dict[str, tuple[int, int, int]] = {}
        for (candidate_player, season, competition_id), count in by_competition.items():
            if candidate_player != player_id:
                continue
            rank = ranks[(competition_id, season)]
            if (season, rank) not in qualifying:
                continue
            previous = candidates.get(competition_id, (rank, 0, 0))
            candidates[competition_id] = (
                min(rank, previous[0]),
                max(count, previous[1]),
                previous[2] + count,
            )
        selected[player_id] = tuple(
            sorted(
                candidates,
                key=lambda competition_id: (
                    candidates[competition_id][0],
                    -candidates[competition_id][1],
                    -candidates[competition_id][2],
                    competition_id,
                ),
            )[:limit]
        )
    return selected


def summarize_outcomes(
    outcomes: Iterable[PlayerOutcome], *, thresholds: tuple[int, ...] = (10, 15, 20)
) -> list[dict[str, int | float]]:
    """Summarize cohort conversion while exposing missing coverage."""

    by_cohort: dict[int, list[PlayerOutcome]] = defaultdict(list)
    for outcome in outcomes:
        by_cohort[outcome.exit_season_start].append(outcome)

    rows: list[dict[str, int | float]] = []
    for exit_season, cohort in sorted(by_cohort.items()):
        for threshold in thresholds:
            statuses = [row.threshold_status[threshold] for row in cohort]
            classified = sum(status != "unknown" for status in statuses)
            established = sum(status == "reached" for status in statuses)
            complete_coverage = sum(row.coverage_complete for row in cohort)
            established_complete = sum(
                row.coverage_complete and row.threshold_status[threshold] == "reached"
                for row in cohort
            )
            sustained_statuses = [row.sustained_status[threshold] for row in cohort]
            sustained_classified = sum(
                status != "unknown" for status in sustained_statuses
            )
            sustained = sum(status == "reached" for status in sustained_statuses)
            sustained_complete = sum(
                row.coverage_complete and row.sustained_status[threshold] == "reached"
                for row in cohort
            )
            rows.append(
                {
                    "exit_season_start": exit_season,
                    "threshold": threshold,
                    "total_players": len(cohort),
                    "classified_players": classified,
                    "complete_coverage_players": complete_coverage,
                    "unknown_players": len(cohort) - classified,
                    "established_players": established,
                    "established_rate_complete_coverage": (
                        established_complete / complete_coverage
                        if complete_coverage
                        else 0.0
                    ),
                    "established_rate_all": established / len(cohort)
                    if cohort
                    else 0.0,
                    "sustained_classified_players": sustained_classified,
                    "sustained_unknown_players": len(cohort) - sustained_classified,
                    "sustained_players": sustained,
                    "sustained_rate_complete_coverage": (
                        sustained_complete / complete_coverage
                        if complete_coverage
                        else 0.0
                    ),
                    "sustained_rate_all": sustained / len(cohort) if cohort else 0.0,
                    "analysis_complete": complete_coverage == len(cohort),
                }
            )
    return rows


def _tier_for_rank(rank: int, labels: Mapping[int, set[str]]) -> str:
    values = sorted(labels.get(rank, {f"T{rank}"}))
    if len(values) == 1:
        return values[0]
    prefixes = {value.split("-", 1)[0] for value in values}
    return prefixes.pop() if len(prefixes) == 1 else values[0]
