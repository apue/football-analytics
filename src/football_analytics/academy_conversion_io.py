"""CSV contracts and artifact writers for academy conversion research."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .academy_conversion import (
    AppearanceRow,
    CompetitionRule,
    CoverageRow,
    ExitCohort,
    IdentityResolution,
    PlayerOutcome,
    RosterCandidate,
    RosterMembership,
    ValidationIssue,
)


def load_roster_memberships(path: Path) -> list[RosterMembership]:
    return _load_csv(
        path,
        ("player_id", "player_name", "academy_id", "season_start", "source_url"),
        lambda row: RosterMembership(
            row["player_id"],
            row["player_name"],
            row["academy_id"],
            int(row["season_start"]),
            row["source_url"],
        ),
    )


def load_roster_candidates(path: Path) -> list[RosterCandidate]:
    return _load_csv(
        path,
        (
            "candidate_id",
            "displayed_name",
            "academy_id",
            "season_start",
            "source_url",
            "source_page",
            "position",
        ),
        lambda row: RosterCandidate(
            row["candidate_id"],
            row["displayed_name"],
            row["academy_id"],
            int(row["season_start"]),
            row["source_url"],
            int(row["source_page"]),
            row["position"],
        ),
    )


def write_roster_candidates(path: Path, candidates: Iterable[RosterCandidate]) -> None:
    rows = [asdict(candidate) for candidate in candidates]
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(path, rows, _ROSTER_CANDIDATE_FIELDS)


def load_identity_resolutions(path: Path) -> list[IdentityResolution]:
    return _load_csv(
        path,
        ("candidate_id", "player_id", "status", "evidence"),
        lambda row: IdentityResolution(
            row["candidate_id"], row["player_id"], row["status"], row["evidence"]
        ),
    )


def write_resolved_rosters(
    output: Path,
    validation: Path,
    memberships: Iterable[RosterMembership],
    issues: Iterable[ValidationIssue],
) -> None:
    membership_rows = [asdict(row) for row in memberships]
    issue_rows = [asdict(issue) for issue in issues]
    output.parent.mkdir(parents=True, exist_ok=True)
    validation.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output, membership_rows, _ROSTER_FIELDS)
    validation.write_text(
        json.dumps(
            {
                "valid": not issue_rows,
                "issue_count": len(issue_rows),
                "issues": issue_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def load_appearances(path: Path) -> list[AppearanceRow]:
    return _load_csv(
        path,
        (
            "player_id",
            "season_start",
            "club_id",
            "competition_id",
            "appearances",
            "source_url",
        ),
        lambda row: AppearanceRow(
            row["player_id"],
            int(row["season_start"]),
            row["club_id"],
            row["competition_id"],
            int(row["appearances"]),
            row["source_url"],
        ),
    )


def load_competition_rules(path: Path) -> list[CompetitionRule]:
    return _load_csv(
        path,
        (
            "competition_id",
            "season_start",
            "tier",
            "tier_rank",
            "eligible_domestic_league",
            "policy_version",
        ),
        lambda row: CompetitionRule(
            row["competition_id"],
            int(row["season_start"]),
            row["tier"],
            int(row["tier_rank"]),
            _parse_bool(row["eligible_domestic_league"]),
            row["policy_version"],
        ),
    )


def load_coverage(path: Path) -> list[CoverageRow]:
    return _load_csv(
        path,
        ("player_id", "season_start", "status", "scope_id", "source_url"),
        lambda row: CoverageRow(
            row["player_id"],
            int(row["season_start"]),
            row["status"],
            row["scope_id"],
            row["source_url"],
        ),
    )


def write_analysis_artifacts(
    output_dir: Path,
    cohorts: Iterable[ExitCohort],
    outcomes: Iterable[PlayerOutcome],
    summary: Iterable[dict[str, int | float]],
    issues: Iterable[ValidationIssue],
    *,
    thresholds: tuple[int, ...],
    provenance: Mapping[str, Any] | None = None,
) -> None:
    """Write normalized, inspectable artifacts for reporting and review."""

    output_dir.mkdir(parents=True, exist_ok=True)
    cohort_rows = [asdict(row) for row in cohorts]
    outcome_rows = []
    for outcome in outcomes:
        for threshold in thresholds:
            outcome_rows.append(
                {
                    "player_id": outcome.player_id,
                    "player_name": outcome.player_name,
                    "exit_season_start": outcome.exit_season_start,
                    "threshold": threshold,
                    "established_tier": outcome.established_tiers[threshold] or "",
                    "sustained_tier": outcome.sustained_tiers[threshold] or "",
                    "status": outcome.threshold_status[threshold],
                    "sustained_status": outcome.sustained_status[threshold],
                    "highest_reached_tier": outcome.highest_reached_tier or "",
                    "coverage_complete": outcome.coverage_complete,
                }
            )
    issue_rows = [asdict(issue) for issue in issues]
    _write_csv(output_dir / "exit_cohorts.csv", cohort_rows, _COHORT_FIELDS)
    _write_csv(
        output_dir / "player_threshold_outcomes.csv", outcome_rows, _OUTCOME_FIELDS
    )
    _write_csv(output_dir / "cohort_summary.csv", list(summary), _SUMMARY_FIELDS)
    (output_dir / "validation.json").write_text(
        json.dumps(
            {
                "valid": not issue_rows,
                "issue_count": len(issue_rows),
                "issues": issue_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    (output_dir / "provenance.json").write_text(
        json.dumps(dict(provenance or {}), ensure_ascii=False, indent=2) + "\n"
    )


def _load_csv[Row](
    path: Path, required: tuple[str, ...], factory: Callable[[dict[str, str]], Row]
) -> list[Row]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [
            field for field in required if field not in (reader.fieldnames or ())
        ]
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        rows = []
        for line_number, row in enumerate(reader, start=2):
            try:
                rows.append(factory({key: value.strip() for key, value in row.items()}))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: invalid row: {exc}") from exc
        return rows


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"invalid boolean: {value}")


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


_COHORT_FIELDS = (
    "player_id",
    "player_name",
    "academy_id",
    "exit_season_start",
    "roster_season_count",
)
_ROSTER_FIELDS = (
    "player_id",
    "player_name",
    "academy_id",
    "season_start",
    "source_url",
)
_ROSTER_CANDIDATE_FIELDS = (
    "candidate_id",
    "displayed_name",
    "academy_id",
    "season_start",
    "source_url",
    "source_page",
    "position",
)
_OUTCOME_FIELDS = (
    "player_id",
    "player_name",
    "exit_season_start",
    "threshold",
    "established_tier",
    "sustained_tier",
    "status",
    "sustained_status",
    "highest_reached_tier",
    "coverage_complete",
)
_SUMMARY_FIELDS = (
    "exit_season_start",
    "threshold",
    "total_players",
    "classified_players",
    "complete_coverage_players",
    "unknown_players",
    "established_players",
    "established_rate_complete_coverage",
    "established_rate_all",
    "sustained_classified_players",
    "sustained_unknown_players",
    "sustained_players",
    "sustained_rate_complete_coverage",
    "sustained_rate_all",
    "analysis_complete",
)
