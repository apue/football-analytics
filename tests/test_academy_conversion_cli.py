import json

import pytest

from football_analytics.academy_conversion_cli import main


def test_manifest_command_writes_stable_jsonl(tmp_path, capsys):
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "manifest.jsonl"
    config_path.write_text(
        json.dumps(
            {
                "provider": "firecrawl",
                "pages": [
                    {"url": "https://example.test/2019", "page_type": "roster"},
                    {"url": "https://example.test/2019", "page_type": "roster"},
                    {"url": "https://example.test/player", "page_type": "career"},
                ],
            }
        )
    )

    assert (
        main(["manifest", "--config", str(config_path), "--output", str(output_path)])
        == 0
    )

    rows = [json.loads(line) for line in output_path.read_text().splitlines()]
    emitted = json.loads(capsys.readouterr().out)
    assert len(rows) == 2
    assert emitted == {"manifest": str(output_path), "item_count": 2}


def test_acquire_refuses_unapproved_source_policy(tmp_path):
    config_path = tmp_path / "config.json"
    manifest_path = tmp_path / "manifest.jsonl"
    config_path.write_text(
        json.dumps(
            {
                "provider": "firecrawl",
                "source_policy": {"status": "pending"},
                "contracts": {},
            }
        )
    )
    manifest_path.write_text("")

    with pytest.raises(SystemExit, match="source policy is not approved"):
        main(
            [
                "acquire",
                "--config",
                str(config_path),
                "--manifest",
                str(manifest_path),
                "--run-dir",
                str(tmp_path / "run"),
                "--env-file",
                str(tmp_path / ".env.local"),
            ]
        )


def test_acquire_downloads_approved_http_file(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.json"
    manifest_path = tmp_path / "manifest.jsonl"
    run_dir = tmp_path / "run"
    config_path.write_text(
        json.dumps(
            {
                "provider": "http-file",
                "source_policy": {"status": "approved"},
                "contracts": {
                    "roster_report": {
                        "content_types": ["application/pdf"],
                        "magic_prefix": "%PDF-",
                        "tail_marker": "%%EOF",
                        "min_bytes": 10,
                    }
                },
            }
        )
    )
    manifest_path.write_text(
        json.dumps(
            {
                "item_id": "report-1",
                "url": "https://example.test/report.pdf",
                "provider": "http-file",
                "page_type": "roster_report",
            }
        )
        + "\n"
    )
    monkeypatch.setattr(
        "football_analytics.academy_conversion_cli.download_http_file",
        lambda _url: (200, "application/pdf", b"%PDF-fixture%%EOF"),
    )

    exit_code = main(
        [
            "acquire",
            "--config",
            str(config_path),
            "--manifest",
            str(manifest_path),
            "--run-dir",
            str(run_dir),
        ]
    )

    emitted = json.loads(capsys.readouterr().out)
    record = json.loads((run_dir / "records" / "report-1.json").read_text())
    assert exit_code == 0
    assert emitted["counts"] == {"complete": 1}
    assert record["status"] == "complete"


def test_validate_run_reports_record_states(tmp_path, capsys):
    records = tmp_path / "records"
    records.mkdir()
    for item_id, status in (("a", "complete"), ("b", "validation_failed")):
        (records / f"{item_id}.json").write_text(
            json.dumps({"item_id": item_id, "status": status})
        )

    exit_code = main(["validate-run", "--run-dir", str(tmp_path)])

    emitted = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert emitted["counts"] == {"complete": 1, "validation_failed": 1}
    assert emitted["ready_for_parse"] is False


def test_analyze_writes_normalized_outcomes_and_summary(tmp_path, capsys):
    rosters = tmp_path / "rosters.csv"
    appearances = tmp_path / "appearances.csv"
    competitions = tmp_path / "competitions.csv"
    coverage = tmp_path / "coverage.csv"
    output_dir = tmp_path / "analysis"
    rosters.write_text(
        "player_id,player_name,academy_id,season_start,source_url\n"
        "p1,Player One,barca-u19,2019,official-report\n"
    )
    appearances.write_text(
        "player_id,season_start,club_id,competition_id,appearances,source_url\n"
        "p1,2020,club,es1,15,official-stats\n"
    )
    competitions.write_text(
        "competition_id,season_start,tier,tier_rank,eligible_domestic_league,policy_version\n"
        "es1,2020,T0,0,true,v1\n"
    )
    coverage.write_text(
        "player_id,season_start,status,scope_id,source_url\n"
        + "".join(
            f"p1,{season},complete,t0-t2-v1,official-stats\n"
            for season in range(2020, 2025)
        )
    )

    exit_code = main(
        [
            "analyze",
            "--rosters",
            str(rosters),
            "--appearances",
            str(appearances),
            "--competitions",
            str(competitions),
            "--coverage",
            str(coverage),
            "--output-dir",
            str(output_dir),
            "--exit-start",
            "2019",
            "--exit-end",
            "2019",
        ]
    )

    emitted = json.loads(capsys.readouterr().out)
    outcome_rows = (output_dir / "player_threshold_outcomes.csv").read_text()
    summary_rows = (output_dir / "cohort_summary.csv").read_text()
    assert exit_code == 0
    assert emitted["player_count"] == 1
    assert "p1,Player One,2019,15,T0,,reached,not_reached,T0,True" in outcome_rows
    assert "2019,15,1,1,1,0,1,1.0,1.0,1,0,0,0.0,0.0,True" in summary_rows
    assert json.loads((output_dir / "validation.json").read_text())["valid"] is True
    provenance = json.loads((output_dir / "provenance.json").read_text())
    assert provenance["policy_versions"] == ["v1"]
    assert provenance["appearance_source_urls"] == ["official-stats"]
    assert provenance["input_artifacts"]["appearances"] == str(appearances)


def test_resolve_rosters_stops_when_any_identity_is_unresolved(tmp_path, capsys):
    candidates = tmp_path / "candidates.csv"
    resolutions = tmp_path / "resolutions.csv"
    output = tmp_path / "rosters.csv"
    validation = tmp_path / "identity-validation.json"
    candidates.write_text(
        "candidate_id,displayed_name,academy_id,season_start,source_url,source_page,position\n"
        "r1,Player One,barca-u19,2019,official-report,180,midfielder\n"
        "r2,Common Name,barca-u19,2019,official-report,180,forward\n"
    )
    resolutions.write_text(
        "candidate_id,player_id,status,evidence\n"
        "r1,p1,confirmed,official-profile\n"
        "r2,,ambiguous,two-matches\n"
    )

    exit_code = main(
        [
            "resolve-rosters",
            "--candidates",
            str(candidates),
            "--resolutions",
            str(resolutions),
            "--output",
            str(output),
            "--validation",
            str(validation),
        ]
    )

    emitted = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert emitted == {"confirmed": 1, "issues": 1, "valid": False}
    assert "p1,Player One,barca-u19,2019,official-report" in output.read_text()
    assert json.loads(validation.read_text())["issues"][0]["key"] == "r2"
