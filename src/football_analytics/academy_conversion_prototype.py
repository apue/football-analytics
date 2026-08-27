"""Adapter for limited match-row datasets used only to test the pipeline."""

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .academy_conversion import (
    AppearanceRow,
    CompetitionRule,
    CoverageRow,
    RosterMembership,
    build_exit_cohorts,
    observation_seasons,
)


@dataclass(frozen=True)
class SourcePlayerLink:
    """Reviewed link from an internal person to one prototype source ID."""

    player_id: str
    source_player_id: str
    status: str
    evidence: str


@dataclass(frozen=True)
class PrototypeFacts:
    """Facts emitted by a partial-coverage prototype adapter."""

    appearances: list[AppearanceRow]
    rules: list[CompetitionRule]
    coverage: list[CoverageRow]


def load_source_player_links(path: Path) -> list[SourcePlayerLink]:
    with path.open(newline="") as handle:
        return [
            SourcePlayerLink(
                row["player_id"],
                row["source_player_id"],
                row["status"],
                row["evidence"],
            )
            for row in csv.DictReader(handle)
        ]


def merge_source_link_proposals(
    base_links: Iterable[SourcePlayerLink],
    proposals: Iterable[SourcePlayerLink],
    *,
    valid_source_ids: set[str],
) -> list[SourcePlayerLink]:
    """Merge reviewed confirmations while failing closed on identity conflicts."""

    base = list(base_links)
    by_player = {row.player_id: row for row in base}
    if len(by_player) != len(base):
        raise ValueError("duplicate player IDs in base links")
    confirmed_base = [
        row for row in base if row.status == "confirmed" and row.source_player_id
    ]
    invalid_base_sources = sorted(
        {
            row.source_player_id
            for row in confirmed_base
            if row.source_player_id not in valid_source_ids
        }
    )
    if invalid_base_sources:
        raise ValueError(
            f"base source IDs not present in source players: {invalid_base_sources}"
        )
    duplicate_base_sources = sorted(
        source_id
        for source_id, count in Counter(
            row.source_player_id for row in confirmed_base
        ).items()
        if count > 1
    )
    if duplicate_base_sources:
        raise ValueError(
            f"duplicate source IDs in base links: {duplicate_base_sources}"
        )
    seen_proposals: set[str] = set()
    used_sources = {
        row.source_player_id: row.player_id
        for row in base
        if row.status == "confirmed" and row.source_player_id
    }
    for proposal in proposals:
        if proposal.player_id in seen_proposals:
            raise ValueError(f"duplicate proposal: {proposal.player_id}")
        seen_proposals.add(proposal.player_id)
        current = by_player.get(proposal.player_id)
        if current is None:
            raise ValueError(
                f"proposal references unknown player: {proposal.player_id}"
            )
        if proposal.status != "confirmed":
            continue
        if not proposal.source_player_id or not proposal.evidence.strip():
            raise ValueError(f"incomplete confirmed proposal: {proposal.player_id}")
        if proposal.source_player_id not in valid_source_ids:
            raise ValueError(
                f"source player {proposal.source_player_id} "
                "not present in source players"
            )
        if current.status == "confirmed" and (
            current.source_player_id != proposal.source_player_id
        ):
            raise ValueError(f"conflicting proposal: {proposal.player_id}")
        owner = used_sources.get(proposal.source_player_id)
        if owner is not None and owner != proposal.player_id:
            raise ValueError(
                f"source player {proposal.source_player_id} already linked to {owner}"
            )
        by_player[proposal.player_id] = proposal
        used_sources[proposal.source_player_id] = proposal.player_id
    return [by_player[row.player_id] for row in base]


def load_source_player_ids(path: Path) -> set[str]:
    with gzip.open(path, "rt", newline="") as handle:
        reader = csv.DictReader(handle)
        if "player_id" not in (reader.fieldnames or ()):
            raise ValueError(f"{path}: missing player_id column")
        return {row["player_id"].strip() for row in reader if row["player_id"].strip()}


def write_source_player_links(path: Path, links: Iterable[SourcePlayerLink]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_rows(
        path,
        ("player_id", "source_player_id", "status", "evidence"),
        [row.__dict__ for row in links],
    )


def load_competition_policy(
    path: Path,
) -> tuple[str, dict[str, tuple[str, int, bool]]]:
    value = json.loads(path.read_text())
    policy_version = str(value["policy_version"])
    ranks = value["tier_ranks"]
    policy = {
        competition_id: (tier, int(ranks[tier]), True)
        for tier, competition_ids in value["tiers"].items()
        for competition_id in competition_ids
    }
    return policy_version, policy


def write_prototype_facts(output_dir: Path, facts: PrototypeFacts) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(
        output_dir / "appearances.csv",
        (
            "player_id",
            "season_start",
            "club_id",
            "competition_id",
            "appearances",
            "source_url",
        ),
        [row.__dict__ for row in facts.appearances],
    )
    _write_rows(
        output_dir / "competitions.csv",
        (
            "competition_id",
            "season_start",
            "tier",
            "tier_rank",
            "eligible_domestic_league",
            "policy_version",
        ),
        [row.__dict__ for row in facts.rules],
    )
    _write_rows(
        output_dir / "coverage.csv",
        ("player_id", "season_start", "status", "scope_id", "source_url"),
        [row.__dict__ for row in facts.coverage],
    )


def build_match_row_prototype_facts(
    memberships: Iterable[RosterMembership],
    links: Iterable[SourcePlayerLink],
    games_path: Path,
    appearances_path: Path,
    competition_policy: Mapping[str, tuple[str, int, bool]],
    *,
    source_url: str,
    scope_id: str,
    exit_start: int = 2015,
    exit_end: int = 2019,
) -> PrototypeFacts:
    """Aggregate one-row-per-match appearances without claiming full coverage."""

    cohorts = build_exit_cohorts(memberships, exit_start=exit_start, exit_end=exit_end)
    seasons_by_player = {
        cohort.player_id: set(observation_seasons(cohort.exit_season_start))
        for cohort in cohorts
    }
    link_rows = list(links)
    duplicate_links = [
        player_id
        for player_id, count in Counter(row.player_id for row in link_rows).items()
        if count > 1
    ]
    if duplicate_links:
        raise ValueError(f"duplicate source links: {sorted(duplicate_links)!r}")
    internal_by_source = {
        row.source_player_id: row.player_id
        for row in link_rows
        if row.status == "confirmed"
        and row.source_player_id
        and row.player_id in seasons_by_player
    }

    relevant_seasons = set().union(*seasons_by_player.values()) if cohorts else set()
    games: dict[str, tuple[int, str]] = {}
    with gzip.open(games_path, "rt", newline="") as handle:
        for row in csv.DictReader(handle):
            competition_id = row["competition_id"]
            season_start = int(row["season"])
            if (
                competition_id in competition_policy
                and season_start in relevant_seasons
            ):
                games[row["game_id"]] = (season_start, competition_id)

    counts: Counter[tuple[str, int, str, str]] = Counter()
    with gzip.open(appearances_path, "rt", newline="") as handle:
        for row in csv.DictReader(handle):
            internal_id = internal_by_source.get(row["player_id"])
            game = games.get(row["game_id"])
            if internal_id is None or game is None:
                continue
            season_start, competition_id = game
            if season_start not in seasons_by_player[internal_id]:
                continue
            counts[
                (
                    internal_id,
                    season_start,
                    row["player_club_id"],
                    competition_id,
                )
            ] += 1

    appearance_facts = [
        AppearanceRow(
            player_id,
            season_start,
            club_id,
            competition_id,
            count,
            source_url,
        )
        for (player_id, season_start, club_id, competition_id), count in sorted(
            counts.items()
        )
    ]
    rules = [
        CompetitionRule(
            competition_id,
            season_start,
            competition_policy[competition_id][0],
            competition_policy[competition_id][1],
            competition_policy[competition_id][2],
            scope_id,
        )
        for competition_id, season_start in sorted(
            {(row.competition_id, row.season_start) for row in appearance_facts}
        )
    ]
    confirmed_internal = set(internal_by_source.values())
    coverage = [
        CoverageRow(
            cohort.player_id,
            season_start,
            "partial" if cohort.player_id in confirmed_internal else "missing",
            scope_id,
            source_url,
        )
        for cohort in cohorts
        for season_start in observation_seasons(cohort.exit_season_start)
    ]
    return PrototypeFacts(appearance_facts, rules, coverage)


def _write_rows(
    path: Path, fields: tuple[str, ...], rows: Iterable[Mapping[str, Any]]
) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
