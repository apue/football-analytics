import json
from urllib.error import HTTPError

import pytest

import football_analytics.academy_conversion_cli as academy_cli
from football_analytics.academy_conversion_cli import main


def _write_study(path, output_dir, *, roster_config=None, academy_id="academy-u19"):
    if roster_config is None:
        roster_config = output_dir.parent / "roster-source.json"
        roster_config.write_text(
            json.dumps(
                {
                    "academy_id": academy_id,
                    "source_policy": {"status": "approved"},
                    "pages": [
                        {"season_start": season, "expected_player_count": 1}
                        for season in (2019, 2020, 2021)
                    ],
                }
            )
        )
    policy = output_dir.parent / "policy.json"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        json.dumps(
            {
                "policy_version": "v1",
                "tier_ranks": {"T0": 0},
                "tiers": {"T0": ["es1"]},
                "competition_metadata": {"es1": {"career_eligible": True}},
            }
        )
    )
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "study_id": "academy-u19-2019-2019",
                "academy": {
                    "academy_id": academy_id,
                    "display_name": "Academy",
                    "squad_name": "U19",
                },
                "cohorts": {
                    "roster_season_start": 2019,
                    "roster_season_end": 2021,
                    "exit_season_start": 2019,
                    "exit_season_end": 2019,
                    "observation_season_count": 5,
                },
                "outcomes": {
                    "primary_appearance_threshold": 15,
                    "sensitivity_thresholds": [10, 15, 20],
                    "sustained_qualifying_seasons": 2,
                    "competition_policy_path": str(policy),
                },
                "roster_source": {
                    "adapter": "official",
                    "config_path": str(roster_config),
                    "policy_status": "approved",
                    "public_url": "https://club.example/academy",
                },
                "adult_source": {
                    "adapter": "licensed",
                    "scope_id": "complete-v1",
                    "policy_status": "approved",
                    "public_url": "https://data.example/careers",
                    "coverage_note": "complete",
                },
                "outputs": {
                    "run_dir": str(output_dir.parent),
                    "report_path": str(output_dir.parent / "report/index.html"),
                    "language": "zh-CN",
                },
            }
        )
    )


def _write_acquisition_study(path, config_path, run_dir, *, approved=True):
    _write_study(path, run_dir / "analysis", roster_config=config_path)
    value = json.loads(path.read_text())
    value["roster_source"]["policy_status"] = "approved" if approved else "pending"
    value["adult_source"]["policy_status"] = "approved"
    path.write_text(json.dumps(value))


def test_health_reports_each_gate_and_runs_parser_probe(tmp_path, monkeypatch, capsys):
    parser_calls = []

    class StubClient:
        def __init__(self, _config):
            pass

        def scrape(self, _url):
            return {
                "success": True,
                "data": {
                    "markdown": "Academy roster",
                    "metadata": {"statusCode": 200},
                },
            }

    monkeypatch.setattr(academy_cli, "load_keypool_config", lambda _path: object())
    monkeypatch.setattr(academy_cli, "FirecrawlClient", StubClient)
    monkeypatch.setattr(
        academy_cli,
        "parse_roster_blocks",
        lambda *args, **kwargs: parser_calls.append((args, kwargs)) or [object()],
    )

    exit_code = main(
        [
            "health",
            "--env-file",
            str(tmp_path / ".env"),
            "--url",
            "https://example.test/roster",
            "--required-text",
            "Academy roster",
        ]
    )

    emitted = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert emitted["checks"] == {
        "keypool": "passed",
        "transport": "passed",
        "firecrawl": "passed",
        "target_page": "passed",
        "content": "passed",
        "parser": "passed",
    }
    assert len(parser_calls) == 1


def test_health_stops_at_failed_target_page_gate(tmp_path, monkeypatch, capsys):
    class StubClient:
        def __init__(self, _config):
            pass

        def scrape(self, _url):
            return {
                "success": True,
                "data": {
                    "markdown": "Method Not Allowed",
                    "metadata": {"statusCode": 405},
                },
            }

    monkeypatch.setattr(academy_cli, "load_keypool_config", lambda _path: object())
    monkeypatch.setattr(academy_cli, "FirecrawlClient", StubClient)

    exit_code = main(
        [
            "health",
            "--env-file",
            str(tmp_path / ".env"),
            "--url",
            "https://example.test/roster",
        ]
    )

    emitted = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert emitted["checks"] == {
        "keypool": "passed",
        "transport": "passed",
        "firecrawl": "passed",
        "target_page": "failed",
        "content": "not_checked",
        "parser": "not_checked",
    }
    assert emitted["error"] == "target_status=405"


def test_health_classifies_firecrawl_http_error_above_target_gate(
    tmp_path, monkeypatch, capsys
):
    class StubClient:
        def __init__(self, _config):
            pass

        def scrape(self, url):
            raise HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(academy_cli, "load_keypool_config", lambda _path: object())
    monkeypatch.setattr(academy_cli, "FirecrawlClient", StubClient)

    exit_code = main(
        [
            "health",
            "--env-file",
            str(tmp_path / ".env"),
            "--url",
            "https://example.test/roster",
        ]
    )

    emitted = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert emitted["checks"] == {
        "keypool": "passed",
        "transport": "passed",
        "firecrawl": "failed",
        "target_page": "not_checked",
        "content": "not_checked",
        "parser": "not_checked",
    }


def test_health_reports_parser_probe_failure(tmp_path, monkeypatch, capsys):
    class StubClient:
        def __init__(self, _config):
            pass

        def scrape(self, _url):
            return {
                "success": True,
                "data": {
                    "markdown": "Academy roster",
                    "metadata": {"statusCode": 200},
                },
            }

    monkeypatch.setattr(academy_cli, "load_keypool_config", lambda _path: object())
    monkeypatch.setattr(academy_cli, "FirecrawlClient", StubClient)
    monkeypatch.setattr(
        academy_cli,
        "parse_roster_blocks",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("broken parser")),
    )

    exit_code = main(
        [
            "health",
            "--env-file",
            str(tmp_path / ".env"),
            "--url",
            "https://example.test/roster",
            "--required-text",
            "Academy roster",
        ]
    )

    emitted = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert emitted["checks"]["content"] == "passed"
    assert emitted["checks"]["parser"] == "failed"


def test_manifest_command_writes_stable_jsonl(tmp_path, capsys):
    config_path = tmp_path / "config.json"
    run_dir = tmp_path / "run"
    output_path = run_dir / "manifest.jsonl"
    study = tmp_path / "study.json"
    _write_acquisition_study(study, config_path, run_dir)
    config_path.write_text(
        json.dumps(
            {
                "provider": "firecrawl",
                "academy_id": "academy-u19",
                "source_policy": {"status": "approved"},
                "pages": [
                    {
                        "url": "https://example.test/2019",
                        "page_type": "roster",
                        "season_start": 2019,
                    },
                    {
                        "url": "https://example.test/2019",
                        "page_type": "roster",
                        "season_start": 2019,
                    },
                    {
                        "url": "https://example.test/player",
                        "page_type": "career",
                        "season_start": 2020,
                    },
                    {
                        "url": "https://example.test/2019",
                        "page_type": "roster",
                        "season_start": 2021,
                    },
                ],
            }
        )
    )

    assert (
        main(
            [
                "manifest",
                "--study-config",
                str(study),
                "--config",
                str(config_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    rows = [json.loads(line) for line in output_path.read_text().splitlines()]
    emitted = json.loads(capsys.readouterr().out)
    assert len(rows) == 2
    assert emitted == {"manifest": str(output_path), "item_count": 2}


def test_acquire_refuses_unapproved_source_policy(tmp_path):
    config_path = tmp_path / "config.json"
    run_dir = tmp_path / "run"
    manifest_path = run_dir / "manifest.jsonl"
    config_path.write_text(
        json.dumps(
            {
                "academy_id": "academy-u19",
                "provider": "firecrawl",
                "source_policy": {"status": "pending"},
                "contracts": {},
                "pages": [
                    {"url": "https://example.test/2019", "season_start": 2019},
                    {"url": "https://example.test/2020", "season_start": 2020},
                    {"url": "https://example.test/2021", "season_start": 2021},
                ],
            }
        )
    )
    study = tmp_path / "study.json"
    _write_acquisition_study(study, config_path, run_dir)
    manifest_path.write_text("")

    with pytest.raises(SystemExit, match="source policy does not match"):
        main(
            [
                "acquire",
                "--study-config",
                str(study),
                "--config",
                str(config_path),
                "--manifest",
                str(manifest_path),
                "--run-dir",
                str(run_dir),
                "--env-file",
                str(tmp_path / ".env.local"),
            ]
        )


def test_acquire_downloads_approved_http_file(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.json"
    run_dir = tmp_path / "run"
    manifest_path = run_dir / "manifest.jsonl"
    study = tmp_path / "study.json"
    _write_acquisition_study(study, config_path, run_dir)
    config_path.write_text(
        json.dumps(
            {
                "academy_id": "academy-u19",
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
                "pages": [
                    {"url": "https://example.test/report.pdf", "season_start": 2019},
                    {
                        "url": "https://example.test/report-2020.pdf",
                        "season_start": 2020,
                    },
                    {
                        "url": "https://example.test/report-2021.pdf",
                        "season_start": 2021,
                    },
                ],
            }
        )
    )
    main(
        [
            "manifest",
            "--study-config",
            str(study),
            "--config",
            str(config_path),
            "--output",
            str(manifest_path),
        ]
    )
    capsys.readouterr()
    monkeypatch.setattr(
        "football_analytics.academy_conversion_cli.download_http_file",
        lambda _url: (200, "application/pdf", b"%PDF-fixture%%EOF"),
    )

    exit_code = main(
        [
            "acquire",
            "--study-config",
            str(study),
            "--config",
            str(config_path),
            "--manifest",
            str(manifest_path),
            "--run-dir",
            str(run_dir),
        ]
    )

    emitted = json.loads(capsys.readouterr().out)
    first_id = json.loads(manifest_path.read_text().splitlines()[0])["item_id"]
    record = json.loads((run_dir / "records" / f"{first_id}.json").read_text())
    assert exit_code == 0
    assert emitted["counts"] == {"complete": 3}
    assert record["status"] == "complete"

    changed = json.loads(manifest_path.read_text().splitlines()[0])
    changed["url"] = "https://example.test/unrelated.pdf"
    manifest_path.write_text(json.dumps(changed) + "\n")
    with pytest.raises(SystemExit, match="manifest does not match"):
        main(
            [
                "acquire",
                "--study-config",
                str(study),
                "--config",
                str(config_path),
                "--manifest",
                str(manifest_path),
                "--run-dir",
                str(run_dir),
            ]
        )


def test_acquire_runs_and_persists_firecrawl_batch_workflow(
    tmp_path, monkeypatch, capsys
):
    config_path = tmp_path / "config.json"
    run_dir = tmp_path / "run"
    manifest = run_dir / "manifest.jsonl"
    study = tmp_path / "study.json"
    _write_acquisition_study(study, config_path, run_dir)
    pages = [
        {
            "url": f"https://example.test/{season}",
            "page_type": "roster",
            "season_start": season,
        }
        for season in (2019, 2020, 2021)
    ]
    config_path.write_text(
        json.dumps(
            {
                "provider": "firecrawl",
                "batch": {"enabled": True, "max_concurrency": 2},
                "academy_id": "academy-u19",
                "source_policy": {"status": "approved"},
                "contracts": {"roster": {"required_text": ["Academy"]}},
                "pages": pages,
            }
        )
    )
    assert (
        main(
            [
                "manifest",
                "--study-config",
                str(study),
                "--config",
                str(config_path),
                "--output",
                str(manifest),
            ]
        )
        == 0
    )
    capsys.readouterr()

    class StubClient:
        def __init__(self, _config):
            pass

        def start_batch_request(self, urls, *, formats, max_concurrency):
            assert list(urls) == [page["url"] for page in pages]
            assert max_concurrency == 2
            return {"success": True, "id": "job-123"}

        def batch_status(self, _job_id):
            return {
                "success": True,
                "status": "completed",
                "data": [
                    {
                        "markdown": f"Academy {page['season_start']}",
                        "metadata": {"sourceURL": page["url"], "statusCode": 200},
                    }
                    for page in pages
                ],
            }

    monkeypatch.setattr(academy_cli, "load_keypool_config", lambda _path: object())
    monkeypatch.setattr(academy_cli, "FirecrawlClient", StubClient)

    exit_code = main(
        [
            "acquire",
            "--study-config",
            str(study),
            "--config",
            str(config_path),
            "--manifest",
            str(manifest),
            "--run-dir",
            str(run_dir),
            "--env-file",
            str(tmp_path / ".env"),
        ]
    )

    emitted = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert emitted["counts"] == {"complete": 3}
    assert emitted["batch"] == {
        "attempt": 1,
        "job_id": "job-123",
        "status": "completed",
    }
    assert len(list((run_dir / "records").glob("*.json"))) == 3
    assert len(list((run_dir / "batches").glob("*.json"))) == 1


def test_validate_run_reports_record_states(tmp_path, capsys):
    config = tmp_path / "source.json"
    study = tmp_path / "study.json"
    _write_acquisition_study(study, config, tmp_path)
    config.write_text(
        json.dumps(
            {
                "academy_id": "academy-u19",
                "provider": "firecrawl",
                "source_policy": {"status": "approved"},
                "pages": [
                    {"url": f"https://example.test/{season}", "season_start": season}
                    for season in (2019, 2020, 2021)
                ],
            }
        )
    )
    manifest = tmp_path / "manifest.jsonl"
    main(
        [
            "manifest",
            "--study-config",
            str(study),
            "--config",
            str(config),
            "--output",
            str(manifest),
        ]
    )
    capsys.readouterr()
    records = tmp_path / "records"
    records.mkdir()
    manifest_rows = [json.loads(line) for line in manifest.read_text().splitlines()]
    for index, row in enumerate(manifest_rows):
        status = "validation_failed" if index == 1 else "complete"
        (records / f"{row['item_id']}.json").write_text(
            json.dumps({"item_id": row["item_id"], "status": status})
        )
    exit_code = main(
        ["validate-run", "--study-config", str(study), "--run-dir", str(tmp_path)]
    )

    emitted = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert emitted["counts"] == {"complete": 2, "validation_failed": 1}
    assert emitted["manifest_matches_study"] is True
    assert emitted["records_match_manifest"] is True
    assert emitted["ready_for_parse"] is False


def test_analyze_writes_normalized_outcomes_and_summary(tmp_path, capsys):
    rosters = tmp_path / "rosters.csv"
    appearances = tmp_path / "appearances.csv"
    competitions = tmp_path / "competitions.csv"
    coverage = tmp_path / "coverage.csv"
    output_dir = tmp_path / "analysis"
    study = tmp_path / "study.json"
    _write_study(study, output_dir)
    rosters.write_text(
        "player_id,player_name,academy_id,season_start,source_url\n"
        "p1,Player One,academy-u19,2019,official-report\n"
        "p2,Boundary Player,academy-u19,2020,official-report\n"
        "p2,Boundary Player,academy-u19,2021,official-report\n"
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
            f"p1,{season},complete,complete-v1,official-stats\n"
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
            "--study-config",
            str(study),
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
    assert provenance["study"]["study_id"] == "academy-u19-2019-2019"

    coverage.write_text(coverage.read_text().replace("complete-v1", "other-scope"))
    with pytest.raises(SystemExit, match="adult-source scope"):
        main(
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
                "--study-config",
                str(study),
            ]
        )


def test_analyze_rejects_rosters_from_another_academy(tmp_path):
    rosters = tmp_path / "rosters.csv"
    study = tmp_path / "study.json"
    output_dir = tmp_path / "analysis"
    _write_study(study, output_dir)
    rosters.write_text(
        "player_id,player_name,academy_id,season_start,source_url\n"
        "p1,Player One,other-academy,2019,official-report\n"
    )
    for name, header in {
        "appearances.csv": (
            "player_id,season_start,club_id,competition_id,appearances,source_url\n"
        ),
        "competitions.csv": (
            "competition_id,season_start,tier,tier_rank,"
            "eligible_domestic_league,policy_version\n"
        ),
        "coverage.csv": "player_id,season_start,status,scope_id,source_url\n",
    }.items():
        (tmp_path / name).write_text(header)

    with pytest.raises(SystemExit, match="do not match study academy"):
        main(
            [
                "analyze",
                "--rosters",
                str(rosters),
                "--appearances",
                str(tmp_path / "appearances.csv"),
                "--competitions",
                str(tmp_path / "competitions.csv"),
                "--coverage",
                str(tmp_path / "coverage.csv"),
                "--output-dir",
                str(output_dir),
                "--study-config",
                str(study),
            ]
        )


def test_analyze_rejects_missing_boundary_roster_seasons(tmp_path):
    rosters = tmp_path / "rosters.csv"
    appearances = tmp_path / "appearances.csv"
    competitions = tmp_path / "competitions.csv"
    coverage = tmp_path / "coverage.csv"
    output_dir = tmp_path / "analysis"
    study = tmp_path / "study.json"
    _write_study(study, output_dir)
    rosters.write_text(
        "player_id,player_name,academy_id,season_start,source_url\n"
        "p1,Player One,academy-u19,2019,official-report\n"
    )
    appearances.write_text(
        "player_id,season_start,club_id,competition_id,appearances,source_url\n"
    )
    competitions.write_text(
        "competition_id,season_start,tier,tier_rank,"
        "eligible_domestic_league,policy_version\n"
        "es1,2020,T0,0,true,v1\n"
    )
    coverage.write_text(
        "player_id,season_start,status,scope_id,source_url\n"
        "p1,2020,complete,complete-v1,official-stats\n"
    )

    with pytest.raises(
        SystemExit,
        match=r"roster facts do not cover configured seasons: missing=\[2020, 2021\]",
    ):
        main(
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
                "--study-config",
                str(study),
            ]
        )


def test_analyze_rejects_incomplete_boundary_roster_season(tmp_path):
    rosters = tmp_path / "rosters.csv"
    appearances = tmp_path / "appearances.csv"
    competitions = tmp_path / "competitions.csv"
    coverage = tmp_path / "coverage.csv"
    output_dir = tmp_path / "analysis"
    study = tmp_path / "study.json"
    _write_study(study, output_dir)
    roster_config = output_dir.parent / "roster-source.json"
    config = json.loads(roster_config.read_text())
    config["pages"][1]["expected_player_count"] = 2
    roster_config.write_text(json.dumps(config))
    rosters.write_text(
        "player_id,player_name,academy_id,season_start,source_url\n"
        "p1,Player One,academy-u19,2019,official-report\n"
        "p2,Boundary Player,academy-u19,2020,official-report\n"
        "p3,Later Boundary,academy-u19,2021,official-report\n"
    )
    appearances.write_text(
        "player_id,season_start,club_id,competition_id,appearances,source_url\n"
    )
    competitions.write_text(
        "competition_id,season_start,tier,tier_rank,"
        "eligible_domestic_league,policy_version\n"
        "es1,2020,T0,0,true,v1\n"
    )
    coverage.write_text(
        "player_id,season_start,status,scope_id,source_url\n"
        "p1,2020,complete,complete-v1,official-stats\n"
    )

    with pytest.raises(
        SystemExit,
        match=(
            r"roster fact count does not match source contract: "
            r"season=2020 actual=1 expected=2"
        ),
    ):
        main(
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
                "--study-config",
                str(study),
            ]
        )


def test_validate_run_rejects_a_different_run_directory(tmp_path):
    configured_run = tmp_path / "configured"
    study = tmp_path / "study.json"
    _write_acquisition_study(study, tmp_path / "source.json", configured_run)

    with pytest.raises(SystemExit, match="run directory does not match"):
        main(
            [
                "validate-run",
                "--study-config",
                str(study),
                "--run-dir",
                str(tmp_path / "other"),
            ]
        )


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
