import csv

from football_analytics.academy_conversion_report import render_report


def _write_csv(path, fields, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_report_labels_partial_results_as_lower_bounds(tmp_path):
    summaries = tmp_path / "summary.csv"
    outcomes = tmp_path / "outcomes.csv"
    rosters = tmp_path / "rosters.csv"
    output = tmp_path / "index.html"
    _write_csv(
        summaries,
        [
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
        ],
        [
            {
                "exit_season_start": 2019,
                "threshold": 15,
                "total_players": 2,
                "classified_players": 1,
                "complete_coverage_players": 0,
                "unknown_players": 1,
                "established_players": 1,
                "established_rate_complete_coverage": 0,
                "established_rate_all": 0.5,
                "sustained_classified_players": 0,
                "sustained_unknown_players": 2,
                "sustained_players": 0,
                "sustained_rate_complete_coverage": 0,
                "sustained_rate_all": 0,
                "analysis_complete": False,
            }
        ],
    )
    _write_csv(
        outcomes,
        [
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
        ],
        [
            {
                "player_id": "p1",
                "player_name": "One",
                "exit_season_start": 2019,
                "threshold": 15,
                "established_tier": "T0",
                "sustained_tier": "",
                "status": "reached",
                "sustained_status": "unknown",
                "highest_reached_tier": "T0",
                "coverage_complete": False,
            },
            {
                "player_id": "p2",
                "player_name": "Two",
                "exit_season_start": 2019,
                "threshold": 15,
                "established_tier": "",
                "sustained_tier": "",
                "status": "unknown",
                "sustained_status": "unknown",
                "highest_reached_tier": "",
                "coverage_complete": False,
            },
        ],
    )
    _write_csv(
        rosters,
        ["player_id", "player_name", "academy_id", "season_start", "source_url"],
        [
            {
                "player_id": "p1",
                "player_name": "One",
                "academy_id": "academy",
                "season_start": 2019,
                "source_url": "official",
            },
            {
                "player_id": "p2",
                "player_name": "Two",
                "academy_id": "academy",
                "season_start": 2019,
                "source_url": "official",
            },
        ],
    )

    render_report(summaries, outcomes, rosters, output)

    html = output.read_text()
    assert "顶级青训的两面" in html
    assert "顶级青训同时生产顶级价值，也生产职业不确定性" in html
    assert "五大联赛顶级联赛" in html
    assert "这不是淘汰漏斗" in html
    assert "对球员与家庭：入选不是承诺" in html
    assert "7 份官方年报中的 roster-season 行" not in html
    assert "底层仍保留可复现" not in html
    assert '"rosterReports"' not in html
    assert '"uniqueRosterPlayers"' not in html
    assert '"analysisComplete":false' in html
    assert '"primaryThreshold":15' in html
    assert '"observedReached":1' in html
    assert '"establishedCount":1' in html
    assert '"unknownCount":1' in html
    assert "One" in html

    summaries_10 = tmp_path / "summary-10.csv"
    outcomes_10 = tmp_path / "outcomes-10.csv"
    with summaries.open(newline="") as handle:
        reader = csv.DictReader(handle)
        summary_rows = [{**row, "threshold": "10"} for row in reader]
        summary_fields = tuple(reader.fieldnames or ())
    with outcomes.open(newline="") as handle:
        reader = csv.DictReader(handle)
        outcome_rows = [{**row, "threshold": "10"} for row in reader]
        outcome_fields = tuple(reader.fieldnames or ())
    _write_csv(summaries_10, summary_fields, summary_rows)
    _write_csv(outcomes_10, outcome_fields, outcome_rows)

    render_report(
        summaries_10,
        outcomes_10,
        rosters,
        tmp_path / "report-10.html",
        primary_threshold=10,
    )

    assert '"primaryThreshold":10' in (tmp_path / "report-10.html").read_text()
