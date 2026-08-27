from football_analytics.academy_conversion import (
    AppearanceRow,
    CompetitionRule,
    CoverageRow,
    ExitCohort,
    IdentityResolution,
    RosterCandidate,
    RosterMembership,
    build_exit_cohorts,
    calculate_player_outcomes,
    observation_seasons,
    resolve_roster_memberships,
    summarize_outcomes,
    validate_research_rows,
)


def test_exit_cohorts_use_each_players_last_observed_roster_season():
    memberships = [
        RosterMembership("p1", "Player One", "barca-u19", 2018, "source-a"),
        RosterMembership("p1", "Player One", "barca-u19", 2019, "source-b"),
        RosterMembership("p2", "Player Two", "barca-u19", 2019, "source-b"),
        RosterMembership("p2", "Player Two", "barca-u19", 2020, "source-c"),
        RosterMembership("p3", "Player Three", "barca-u19", 2015, "source-d"),
    ]

    cohorts = build_exit_cohorts(memberships, exit_start=2015, exit_end=2019)

    assert [(row.player_id, row.exit_season_start) for row in cohorts] == [
        ("p3", 2015),
        ("p1", 2019),
    ]


def test_observation_window_is_exactly_five_seasons_after_exit():
    assert observation_seasons(2019) == (2020, 2021, 2022, 2023, 2024)


def test_outcomes_do_not_add_different_tiers_to_cross_threshold():
    memberships = [RosterMembership("p1", "Player One", "academy", 2019, "source")]
    cohorts = build_exit_cohorts(memberships, exit_start=2019, exit_end=2019)
    appearances = [
        AppearanceRow("p1", 2020, "club-a", "top", 8, "source-top"),
        AppearanceRow("p1", 2020, "club-b", "second", 9, "source-second"),
        AppearanceRow("p1", 2021, "club-b", "second", 15, "source-second-2"),
        AppearanceRow("p1", 2022, "club-c", "top", 15, "source-top-2"),
    ]
    rules = [
        CompetitionRule("top", 2020, "T0", 0, True),
        CompetitionRule("second", 2020, "T1-A", 1, True),
        CompetitionRule("second", 2021, "T1-A", 1, True),
        CompetitionRule("top", 2022, "T0", 0, True),
    ]
    coverage = [
        CoverageRow("p1", year, "complete", "scope", "source")
        for year in range(2020, 2025)
    ]

    outcome = calculate_player_outcomes(
        cohorts, appearances, rules, coverage, thresholds=(15,)
    )[0]

    assert outcome.highest_reached_tier == "T0"
    assert outcome.established_tiers[15] == "T0"
    assert outcome.sustained_tiers[15] == "T1-A"
    assert outcome.threshold_status[15] == "reached"
    assert outcome.sustained_status[15] == "reached"


def test_below_threshold_is_unknown_when_observation_coverage_is_partial():
    memberships = [RosterMembership("p1", "Player One", "academy", 2019, "source")]
    cohorts = build_exit_cohorts(memberships, exit_start=2019, exit_end=2019)
    appearances = [AppearanceRow("p1", 2020, "club", "second", 4, "source")]
    rules = [CompetitionRule("second", 2020, "T1-A", 1, True)]
    coverage = [
        CoverageRow("p1", 2020, "complete", "scope", "source"),
        CoverageRow("p1", 2021, "partial", "scope", "source"),
        CoverageRow("p1", 2022, "complete", "scope", "source"),
        CoverageRow("p1", 2023, "complete", "scope", "source"),
        CoverageRow("p1", 2024, "complete", "scope", "source"),
    ]

    outcome = calculate_player_outcomes(
        cohorts, appearances, rules, coverage, thresholds=(15,)
    )[0]

    assert outcome.established_tiers[15] is None
    assert outcome.threshold_status[15] == "unknown"
    assert outcome.sustained_status[15] == "unknown"


def test_validation_rejects_duplicate_facts_and_bad_coverage_status():
    memberships = [
        RosterMembership("p1", "Player", "barca", 2019, "source"),
        RosterMembership("p1", "Player", "barca", 2019, "source"),
    ]
    appearances = [AppearanceRow("p1", 2020, "c1", "es1", -1, "source")]
    rules = [CompetitionRule("es1", 2020, "T0", 0, True)]
    coverage = [CoverageRow("p1", 2020, "maybe")]

    issues = validate_research_rows(memberships, appearances, rules, coverage)

    assert {issue.code for issue in issues} == {
        "duplicate_roster_membership",
        "negative_appearances",
        "invalid_coverage_status",
        "missing_coverage_source",
    }


def test_validation_rejects_unclassified_appearance_competition():
    issues = validate_research_rows(
        [RosterMembership("p1", "Player", "barca", 2019, "source")],
        [AppearanceRow("p1", 2020, "club", "unknown-league", 4, "source")],
        [],
        [CoverageRow("p1", 2020, "complete", "tier-policy-v1", "source")],
    )

    assert [(issue.code, issue.key) for issue in issues] == [
        ("missing_competition_rule", "unknown-league|2020")
    ]


def test_summary_separates_known_denominator_from_unknowns():
    outcomes = calculate_player_outcomes(
        [
            ExitCohort("p1", "One", "barca", 2019, 1),
            ExitCohort("p2", "Two", "barca", 2019, 1),
            ExitCohort("p3", "Three", "barca", 2019, 1),
        ],
        [AppearanceRow("p1", 2020, "c1", "es1", 15, "source")],
        [CompetitionRule("es1", 2020, "T0", 0, True)],
        [
            CoverageRow(player, season, "complete", "scope", "source")
            for player in ("p1", "p2")
            for season in range(2020, 2025)
        ],
        thresholds=(15,),
    )

    summary = summarize_outcomes(outcomes, thresholds=(15,))

    assert summary[0] == {
        "exit_season_start": 2019,
        "threshold": 15,
        "total_players": 3,
        "classified_players": 2,
        "complete_coverage_players": 2,
        "unknown_players": 1,
        "established_players": 1,
        "established_rate_complete_coverage": 0.5,
        "established_rate_all": 1 / 3,
        "sustained_classified_players": 2,
        "sustained_unknown_players": 1,
        "sustained_players": 0,
        "sustained_rate_complete_coverage": 0.0,
        "sustained_rate_all": 0.0,
        "analysis_complete": False,
    }


def test_roster_identity_resolution_quarantines_unconfirmed_candidates():
    candidates = [
        RosterCandidate("r1", "Player One", "barca", 2019, "report", 180),
        RosterCandidate("r2", "Common Name", "barca", 2019, "report", 180),
    ]
    resolutions = [
        IdentityResolution("r1", "p1", "confirmed", "official profile"),
        IdentityResolution("r2", "", "ambiguous", "two candidates"),
    ]

    memberships, issues = resolve_roster_memberships(candidates, resolutions)

    assert memberships == [
        RosterMembership("p1", "Player One", "barca", 2019, "report")
    ]
    assert [(issue.code, issue.key) for issue in issues] == [
        ("unresolved_roster_identity", "r2")
    ]


def test_validation_rejects_unknown_players_and_incomplete_coverage_evidence():
    issues = validate_research_rows(
        [RosterMembership("p1", "Player", "barca", 2019, "source")],
        [AppearanceRow("unknown", 2020, "club", "es1", 4, "source")],
        [CompetitionRule("es1", 2020, "T0", 0, True)],
        [CoverageRow("unknown", 2020, "complete", "", "")],
    )

    assert {issue.code for issue in issues} == {
        "appearance_player_not_in_roster",
        "coverage_player_not_in_roster",
        "missing_coverage_scope",
        "missing_coverage_source",
    }
