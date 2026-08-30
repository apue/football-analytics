import csv
import json

from football_analytics.academy_baseline import verify_analysis_baseline


def _write_csv(path, fields, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_verify_analysis_baseline_compares_stable_business_counts(tmp_path):
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    (analysis / "validation.json").write_text(json.dumps({"valid": True}))
    _write_csv(
        analysis / "exit_cohorts.csv",
        ["player_id", "exit_season_start"],
        [
            {"player_id": "p1", "exit_season_start": "2019"},
            {"player_id": "p2", "exit_season_start": "2019"},
        ],
    )
    _write_csv(
        analysis / "player_threshold_outcomes.csv",
        ["player_id", "threshold", "status", "sustained_status"],
        [
            {
                "player_id": "p1",
                "threshold": "15",
                "status": "reached",
                "sustained_status": "reached",
            },
            {
                "player_id": "p2",
                "threshold": "15",
                "status": "unknown",
                "sustained_status": "unknown",
            },
        ],
    )
    coverage = tmp_path / "coverage.csv"
    _write_csv(
        coverage,
        ["status"],
        [{"status": "partial"}, {"status": "missing"}],
    )
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "player_count": 2,
                "exit_cohorts": {"2019": 2},
                "coverage": {
                    "total": 2,
                    "complete": 0,
                    "partial": 1,
                    "missing": 1,
                },
                "thresholds": {"15": {"established": 1, "sustained": 1, "unknown": 1}},
            }
        )
    )

    result = verify_analysis_baseline(analysis, coverage, baseline)

    assert result["valid"] is True
    assert result["differences"] == []
