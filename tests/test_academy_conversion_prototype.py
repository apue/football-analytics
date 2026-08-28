import csv
import gzip
import json

from football_analytics.academy_conversion import RosterMembership
from football_analytics.academy_conversion_prototype import (
    SourcePlayerLink,
    build_match_row_prototype_facts,
    load_competition_policy,
    merge_source_link_proposals,
)


def test_competition_policy_keeps_career_eligibility_separate_from_tier(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "policy_version": "v1",
                "tier_ranks": {"PRO": 2},
                "tiers": {"PRO": ["eligible", "excluded"]},
                "competition_metadata": {
                    "eligible": {"career_eligible": True},
                    "excluded": {"career_eligible": False},
                },
            }
        )
    )

    version, policy = load_competition_policy(path)

    assert version == "v1"
    assert policy == {
        "eligible": ("PRO", 2, True),
        "excluded": ("PRO", 2, False),
    }


def test_merge_source_link_proposals_accepts_only_confirmed_non_conflicts():
    merged = merge_source_link_proposals(
        [
            SourcePlayerLink("p1", "", "unmatched", "none"),
            SourcePlayerLink("p2", "source-2", "confirmed", "exact"),
        ],
        [
            SourcePlayerLink("p1", "source-1", "confirmed", "official evidence"),
            SourcePlayerLink("p2", "", "unresolved", "no change"),
        ],
        valid_source_ids={"source-1", "source-2"},
    )

    assert merged == [
        SourcePlayerLink("p1", "source-1", "confirmed", "official evidence"),
        SourcePlayerLink("p2", "source-2", "confirmed", "exact"),
    ]


def test_merge_source_link_proposals_rejects_unknown_players_and_conflicts():
    base = [SourcePlayerLink("p1", "source-1", "confirmed", "exact")]

    for proposal in (
        SourcePlayerLink("missing", "source-2", "confirmed", "evidence"),
        SourcePlayerLink("p1", "source-3", "confirmed", "different evidence"),
    ):
        try:
            merge_source_link_proposals(
                base, [proposal], valid_source_ids={"source-1", "source-2"}
            )
        except ValueError:
            pass
        else:
            raise AssertionError("invalid proposal should fail closed")


def test_merge_source_link_proposals_rejects_missing_source_id():
    try:
        merge_source_link_proposals(
            [SourcePlayerLink("p1", "", "unmatched", "none")],
            [SourcePlayerLink("p1", "missing", "confirmed", "evidence")],
            valid_source_ids={"source-1"},
        )
    except ValueError as exc:
        assert "not present in source players" in str(exc)
    else:
        raise AssertionError("missing source ID should fail closed")


def _write_gzip_csv(path, fields, rows):
    with gzip.open(path, "wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_prototype_adapter_counts_match_rows_and_marks_coverage_partial(tmp_path):
    games = tmp_path / "games.csv.gz"
    appearances = tmp_path / "appearances.csv.gz"
    _write_gzip_csv(
        games,
        ["game_id", "competition_id", "season"],
        [
            {"game_id": "g1", "competition_id": "ES1", "season": "2020"},
            {"game_id": "g2", "competition_id": "ES1", "season": "2020"},
            {"game_id": "g3", "competition_id": "CDR", "season": "2020"},
        ],
    )
    _write_gzip_csv(
        appearances,
        ["game_id", "player_id", "player_club_id", "competition_id"],
        [
            {
                "game_id": "g1",
                "player_id": "source-1",
                "player_club_id": "club",
                "competition_id": "ES1",
            },
            {
                "game_id": "g2",
                "player_id": "source-1",
                "player_club_id": "club",
                "competition_id": "ES1",
            },
            {
                "game_id": "g3",
                "player_id": "source-1",
                "player_club_id": "club",
                "competition_id": "CDR",
            },
        ],
    )

    facts = build_match_row_prototype_facts(
        [
            RosterMembership("p1", "One", "academy", 2019, "roster"),
            RosterMembership("p2", "Two", "academy", 2019, "roster"),
        ],
        [
            SourcePlayerLink("p1", "source-1", "confirmed", "exact"),
            SourcePlayerLink("p2", "", "unresolved", "missing"),
        ],
        games,
        appearances,
        {"ES1": ("T0", 0, True), "CDR": ("excluded", 99, False)},
        source_url="prototype-dataset",
        policy_version="competition-policy-v1",
        coverage_scope_id="prototype-v1-partial",
    )

    assert len(facts.appearances) == 2
    assert (
        next(
            row.appearances for row in facts.appearances if row.competition_id == "ES1"
        )
        == 2
    )
    assert {(row.player_id, row.status) for row in facts.coverage} == {
        ("p1", "partial"),
        ("p2", "missing"),
    }
    assert {row.policy_version for row in facts.rules} == {"competition-policy-v1"}
    assert {row.scope_id for row in facts.coverage} == {"prototype-v1-partial"}
