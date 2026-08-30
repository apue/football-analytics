import csv
import json

import pytest

from football_analytics.academy_conversion_report import render_report


def _write_csv(path, fields, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_study(
    path,
    policy,
    output,
    *,
    thresholds=(15,),
    primary=15,
    observation_seasons=5,
    sustained_seasons=2,
):
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "study_id": "real-madrid-u19-2019-2019",
                "academy": {
                    "academy_id": "real-madrid-u19",
                    "display_name": "皇马青训",
                    "squad_name": "Real Madrid U19",
                },
                "cohorts": {
                    "roster_season_start": 2019,
                    "roster_season_end": 2021,
                    "exit_season_start": 2019,
                    "exit_season_end": 2019,
                    "observation_season_count": observation_seasons,
                },
                "outcomes": {
                    "primary_appearance_threshold": primary,
                    "sensitivity_thresholds": list(thresholds),
                    "sustained_qualifying_seasons": sustained_seasons,
                    "competition_policy_path": str(policy),
                },
                "roster_source": {
                    "config_path": str(path.parent / "roster-source.json"),
                    "evidence_path": str(path.parent / "evidence.jsonl"),
                    "policy_status": "approved",
                    "public_url": "https://club.example/academy",
                },
                "adult_source": {
                    "scope_id": "complete-v1",
                    "policy_status": "approved",
                    "public_url": "https://data.example/careers",
                    "coverage_note": "完整覆盖声明范围内的职业联赛。",
                },
                "outputs": {
                    "run_dir": str(output.parent),
                    "report_path": str(output),
                },
            }
        )
    )


def test_report_uses_study_identity_bands_and_real_leagues(tmp_path):
    summaries = tmp_path / "summary.csv"
    outcomes = tmp_path / "outcomes.csv"
    appearances = tmp_path / "appearances.csv"
    competitions = tmp_path / "competitions.csv"
    policy = tmp_path / "policy.json"
    study = tmp_path / "study.json"
    output = tmp_path / "index.html"
    _write_csv(
        summaries,
        [
            "exit_season_start",
            "threshold",
            "total_players",
            "established_players",
            "sustained_players",
            "analysis_complete",
        ],
        [
            {
                "exit_season_start": 2019,
                "threshold": 15,
                "total_players": 2,
                "established_players": 1,
                "sustained_players": 0,
                "analysis_complete": True,
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
                "established_tier": "ELITE",
                "sustained_tier": "",
                "status": "reached",
                "sustained_status": "not_reached",
                "highest_reached_tier": "ELITE",
                "coverage_complete": True,
            },
            {
                "player_id": "p2",
                "player_name": "Two",
                "exit_season_start": 2019,
                "threshold": 15,
                "established_tier": "",
                "sustained_tier": "",
                "status": "not_reached",
                "sustained_status": "not_reached",
                "highest_reached_tier": "",
                "coverage_complete": True,
            },
        ],
    )
    _write_csv(
        appearances,
        [
            "player_id",
            "season_start",
            "club_id",
            "competition_id",
            "appearances",
            "source_url",
        ],
        [
            {
                "player_id": "p1",
                "season_start": 2020,
                "club_id": "c1",
                "competition_id": "ES1",
                "appearances": 18,
                "source_url": "adult-source",
            }
        ],
    )
    _write_csv(
        competitions,
        [
            "competition_id",
            "season_start",
            "tier",
            "tier_rank",
            "eligible_domestic_league",
            "policy_version",
        ],
        [
            {
                "competition_id": "ES1",
                "season_start": 2020,
                "tier": "ELITE",
                "tier_rank": 0,
                "eligible_domestic_league": True,
                "policy_version": "v1",
            }
        ],
    )
    policy.write_text(
        json.dumps(
            {
                "policy_version": "v1",
                "tier_labels_zh": {"ELITE": "五大联赛"},
                "reporting_bands": [
                    {
                        "id": "professional",
                        "label_zh": "职业联赛",
                        "detail_zh": "所有职业联赛",
                        "tiers": None,
                    },
                    {
                        "id": "higher-level",
                        "label_zh": "较高水平职业联赛",
                        "detail_zh": "选定高水平联赛",
                        "tiers": ["ELITE"],
                    },
                    {
                        "id": "big-five",
                        "label_zh": "五大联赛",
                        "detail_zh": "五大联赛顶级联赛",
                        "tiers": ["ELITE"],
                    },
                ],
                "competition_metadata": {"ES1": {"name_zh": "西甲"}},
            }
        )
    )
    _write_study(
        study,
        policy,
        output,
        observation_seasons=6,
        sustained_seasons=3,
    )

    rendered = render_report(summaries, outcomes, appearances, competitions, study)

    html = rendered.read_text()
    assert rendered == output
    assert '"academyName":"皇马青训"' in html
    assert '"squadName":"Real Madrid U19"' in html
    assert '"observationSeasons":6' in html
    assert '"sustainedSeasons":3' in html
    assert '"representative_leagues":"西甲"' in html
    assert '"id":"professional"' in html
    assert '"established":1' in html
    assert "完整观察下未达标" in html
    assert "足球解释" in html
    assert "指标结果" in html
    assert "数据事实" in html
    assert "至少两个赛季" not in html
    assert "五年内站稳" not in html
    assert "巴萨" not in html
    assert " / 85" not in html
    assert '"analysisComplete"' not in html
    assert '"observedReached"' not in html


def test_report_rejects_thresholds_that_disagree_with_study(tmp_path):
    summary = tmp_path / "summary.csv"
    outcomes = tmp_path / "outcomes.csv"
    appearances = tmp_path / "appearances.csv"
    competitions = tmp_path / "competitions.csv"
    policy = tmp_path / "policy.json"
    study = tmp_path / "study.json"
    output = tmp_path / "index.html"
    _write_csv(summary, ["analysis_complete"], [{"analysis_complete": True}])
    _write_csv(
        outcomes,
        ["threshold"],
        [{"threshold": 10}],
    )
    _write_csv(
        appearances,
        [
            "player_id",
            "season_start",
            "club_id",
            "competition_id",
            "appearances",
            "source_url",
        ],
        [],
    )
    _write_csv(
        competitions,
        [
            "competition_id",
            "season_start",
            "tier",
            "tier_rank",
            "eligible_domestic_league",
            "policy_version",
        ],
        [
            {
                "competition_id": "ES1",
                "season_start": 2020,
                "tier": "ELITE",
                "tier_rank": 0,
                "eligible_domestic_league": True,
                "policy_version": "v1",
            }
        ],
    )
    policy.write_text(json.dumps({"policy_version": "v1"}))
    _write_study(study, policy, output, thresholds=(15,), primary=15)

    with pytest.raises(ValueError, match="outcome thresholds do not match"):
        render_report(summary, outcomes, appearances, competitions, study)
