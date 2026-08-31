import csv
import json
from pathlib import Path

from football_analytics.academy_analysis import run_academy_analysis
from football_analytics.academy_baseline import verify_analysis_baseline

ROOT = Path(__file__).resolve().parents[1]


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


def test_committed_barcelona_facts_reproduce_frozen_baseline(tmp_path):
    fixtures = ROOT / "tests/fixtures/academy_conversion/barcelona"
    analysis_dir = tmp_path / "analysis"
    study_value = json.loads(
        (
            ROOT
            / "config/academy_conversion/studies/barcelona-juvenil-a-2015-2019.json"
        ).read_text()
    )
    study_value["roster_source"]["config_path"] = str(
        ROOT / "config/academy_conversion/barcelona_juvenil_a_rosters.json"
    )
    study_value["roster_source"]["evidence_path"] = str(
        ROOT / "config/academy_conversion/barcelona_approved_sources.jsonl"
    )
    study_value["outcomes"]["competition_policy_path"] = str(
        ROOT / "config/academy_conversion/competition_policy_v1.json"
    )
    study_value["outputs"] = {
        "run_dir": str(tmp_path),
        "report_path": str(tmp_path / "report/index.html"),
    }
    study_path = tmp_path / "study.json"
    study_path.write_text(json.dumps(study_value))

    result = run_academy_analysis(
        study_config_path=study_path,
        rosters_path=fixtures / "roster_memberships.csv",
        appearances_path=fixtures / "appearances.csv",
        competitions_path=fixtures / "competitions.csv",
        coverage_path=fixtures / "coverage.csv",
        output_dir=analysis_dir,
    )
    baseline = verify_analysis_baseline(
        analysis_dir,
        fixtures / "coverage.csv",
        ROOT / "config/academy_conversion/barcelona_baseline.json",
    )

    assert result == {"valid": True, "issue_count": 0, "player_count": 85}
    assert baseline["valid"] is True
    assert baseline["differences"] == []
