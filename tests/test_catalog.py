from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from football_analytics.catalog import (
    CatalogError,
    build_catalog,
    ensure_catalog,
    execute_readonly_query,
    fetch_matches,
    list_matches,
    list_seasons,
    normalize_search,
    read_catalog_status,
    resolve_entity,
)


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def manager(manager_id: int, name: str, nickname: str) -> dict[str, object]:
    return {
        "id": manager_id,
        "name": name,
        "nickname": nickname,
        "dob": "1971-01-18",
        "country": {"id": 214, "name": "Spain"},
    }


def team(
    side: str,
    team_id: int,
    name: str,
    team_manager: dict[str, object],
) -> dict[str, object]:
    return {
        f"{side}_team_id": team_id,
        f"{side}_team_name": name,
        f"{side}_team_gender": "male",
        f"{side}_team_group": None,
        "country": {"id": 214, "name": "Spain"},
        "managers": [team_manager],
    }


def match(
    match_id: int,
    match_date: str,
    home: dict[str, object],
    away: dict[str, object],
) -> dict[str, object]:
    return {
        "match_id": match_id,
        "match_date": match_date,
        "kick_off": "20:00:00.000",
        "competition_stage": {"id": 1, "name": "Regular Season"},
        "home_team": home,
        "away_team": away,
        "home_score": 1,
        "away_score": 2,
        "match_status": "available",
        "last_updated": f"{match_date}T23:00:00",
    }


@pytest.fixture
def source_repository(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "open-data"
    source.mkdir()
    run("git", "init", "-b", "main", cwd=source)
    run("git", "config", "user.name", "Test User", cwd=source)
    run("git", "config", "user.email", "test@example.com", cwd=source)

    competitions = [
        {
            "competition_id": 11,
            "season_id": 1,
            "country_name": "Spain",
            "competition_name": "La Liga",
            "competition_gender": "male",
            "competition_youth": False,
            "competition_international": False,
            "season_name": "2022/2023",
        },
        {
            "competition_id": 11,
            "season_id": 2,
            "country_name": "Spain",
            "competition_name": "La Liga",
            "competition_gender": "male",
            "competition_youth": False,
            "competition_international": False,
            "season_name": "2023/2024",
        },
    ]
    pep = manager(36, "Josep Guardiola i Sala", "Pep Guardiola")
    other = manager(99, "José Martínez", "Jose Martinez")
    barcelona_home = team("home", 217, "Barcelona", pep)
    barcelona_away = team("away", 217, "Barcelona", pep)
    madrid_home = team("home", 220, "Real Madrid", other)
    madrid_away = team("away", 220, "Real Madrid", other)

    (source / "data" / "matches" / "11").mkdir(parents=True)
    (source / "data" / "events").mkdir()
    (source / "data" / "lineups").mkdir()
    (source / "data" / "three-sixty").mkdir()
    (source / "data" / "competitions.json").write_text(json.dumps(competitions))
    (source / "data" / "matches" / "11" / "1.json").write_text(
        json.dumps([match(100, "2023-01-01", madrid_home, barcelona_away)])
    )
    (source / "data" / "matches" / "11" / "2.json").write_text(
        json.dumps([match(101, "2024-01-01", barcelona_home, madrid_away)])
    )
    for directory in ("events", "lineups"):
        for match_id in (100, 101):
            (source / "data" / directory / f"{match_id}.json").write_text("[]")
    (source / "data" / "three-sixty" / "101.json").write_text("[]")
    run("git", "add", "data", cwd=source)
    run("git", "commit", "-m", "Add catalog fixture", cwd=source)

    aliases = tmp_path / "aliases.json"
    aliases.write_text(
        json.dumps(
            {
                "competitions": {"11": ["西甲"]},
                "managers": {"36": ["Guardiola", "瓜迪奥拉"]},
                "teams": {
                    "217": ["Barça", "巴塞罗那"],
                    "220": ["皇马"],
                },
            }
        )
    )
    return source, aliases


@pytest.fixture
def built_catalog(
    tmp_path: Path,
    source_repository: tuple[Path, Path],
) -> tuple[Path, Path, Path, datetime]:
    source, aliases = source_repository
    database = tmp_path / "catalog.sqlite"
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    build_catalog(
        source,
        database,
        alias_path=aliases,
        now=timestamp,
        last_attempted_at=timestamp,
        last_successful_check_at=timestamp,
    )
    return source, aliases, database, timestamp


def test_normalize_search_handles_accents_case_and_punctuation() -> None:
    assert normalize_search("  JOSÉ  Martínez! ") == "jose martinez"
    assert normalize_search("Barça") == "barca"


def test_catalog_resolves_names_and_queries_stable_ids(
    built_catalog: tuple[Path, Path, Path, datetime],
) -> None:
    _, _, database, _ = built_catalog

    alias = resolve_entity(database, "team", "巴塞罗那")
    typo = resolve_entity(database, "manager", "Guadiola")
    seasons = list_seasons(database, competition_id=11, team_id=220)
    managed_matches = list_matches(database, team_id=217, manager_id=36, limit=None)
    wrong_team = list_matches(database, team_id=220, manager_id=36, limit=None)

    assert alias["status"] == "resolved"
    assert alias["candidates"][0]["id"] == 217
    assert typo["status"] == "resolution_required"
    assert typo["candidates"][0]["id"] == 36
    assert [season["season_id"] for season in seasons] == [2, 1]
    assert [item["match_id"] for item in managed_matches] == [100, 101]
    assert wrong_team == []


def test_catalog_reports_coverage_and_exposes_readonly_views(
    built_catalog: tuple[Path, Path, Path, datetime],
) -> None:
    _, _, database, _ = built_catalog

    latest = list_seasons(database, competition_id=11, team_id=220, limit=1)[0]
    rows = execute_readonly_query(
        database,
        """
        SELECT match_id, has_360
        FROM catalog_matches
        ORDER BY match_id
        """,
    )

    assert latest["season_id"] == 2
    assert latest["available_match_count"] == 1
    assert latest["three_sixty_match_count"] == 1
    assert latest["coverage_status"] == "unverified"
    assert rows == [
        {"match_id": 100, "has_360": 0},
        {"match_id": 101, "has_360": 1},
    ]
    with pytest.raises(CatalogError, match="must start with"):
        execute_readonly_query(database, "DELETE FROM matches")
    with pytest.raises(CatalogError, match="one statement"):
        execute_readonly_query(
            database,
            "SELECT * FROM catalog_matches; DELETE FROM matches",
        )


def test_catalog_freshness_refresh_and_failure_backoff(
    built_catalog: tuple[Path, Path, Path, datetime],
) -> None:
    source, aliases, database, timestamp = built_catalog

    def unexpected_sync(_: Path) -> bool:
        raise AssertionError("fresh catalog must not contact upstream")

    fresh = ensure_catalog(
        source,
        database,
        alias_path=aliases,
        now=timestamp + timedelta(days=1),
        sync_upstream=unexpected_sync,
    )
    unchanged = ensure_catalog(
        source,
        database,
        alias_path=aliases,
        now=timestamp + timedelta(days=8),
        sync_upstream=lambda _: False,
    )

    def failed_sync(_: Path) -> bool:
        raise CatalogError("network unavailable")

    failed_at = timestamp + timedelta(days=16)
    failed = ensure_catalog(
        source,
        database,
        alias_path=aliases,
        now=failed_at,
        sync_upstream=failed_sync,
    )
    backoff = ensure_catalog(
        source,
        database,
        alias_path=aliases,
        now=failed_at + timedelta(minutes=30),
        sync_upstream=unexpected_sync,
    )

    assert fresh["action"] == "fresh"
    assert unchanged["action"] == "unchanged"
    assert unchanged["last_successful_check_at"].startswith("2026-01-09")
    assert failed["action"] == "failed"
    assert failed["last_error"] == "network unavailable"
    assert backoff["action"] == "backoff"
    assert len(list_matches(database, limit=None)) == 2


def test_changed_source_rebuilds_atomically(
    built_catalog: tuple[Path, Path, Path, datetime],
) -> None:
    source, aliases, database, timestamp = built_catalog
    match_path = source / "data" / "matches" / "11" / "2.json"
    matches = json.loads(match_path.read_text())
    duplicate = {**matches[0], "match_id": 102, "match_date": "2024-02-01"}
    matches.append(duplicate)
    match_path.write_text(json.dumps(matches))
    (source / "data" / "events" / "102.json").write_text("[]")
    (source / "data" / "lineups" / "102.json").write_text("[]")
    run("git", "add", "data", cwd=source)
    run("git", "commit", "-m", "Add new match", cwd=source)

    rebuilt = ensure_catalog(
        source,
        database,
        alias_path=aliases,
        force=True,
        now=timestamp + timedelta(days=1),
        sync_upstream=lambda _: True,
    )

    assert rebuilt["action"] == "rebuilt"
    assert [item["match_id"] for item in list_matches(database, limit=None)] == [
        100,
        101,
        102,
    ]
    assert not list(database.parent.glob(f".{database.name}.*.tmp"))


def test_catalog_rebuilds_after_checkout_was_updated_outside_catalog(
    built_catalog: tuple[Path, Path, Path, datetime],
) -> None:
    source, aliases, database, timestamp = built_catalog
    match_path = source / "data" / "matches" / "11" / "2.json"
    matches = json.loads(match_path.read_text())
    matches.append({**matches[0], "match_id": 103, "match_date": "2024-03-01"})
    match_path.write_text(json.dumps(matches))
    (source / "data" / "events" / "103.json").write_text("[]")
    (source / "data" / "lineups" / "103.json").write_text("[]")
    run("git", "add", "data", cwd=source)
    run("git", "commit", "-m", "Update checkout outside catalog", cwd=source)

    rebuilt = ensure_catalog(
        source,
        database,
        alias_path=aliases,
        force=True,
        now=timestamp + timedelta(days=1),
        sync_upstream=lambda _: False,
    )

    assert rebuilt["action"] == "rebuilt"
    assert list_matches(database, limit=None)[-1]["match_id"] == 103


def test_fetch_uses_catalog_commit_and_reports_unavailable_files(
    built_catalog: tuple[Path, Path, Path, datetime],
) -> None:
    source, _, database, _ = built_catalog

    fetched = fetch_matches(source, database, [100])

    assert fetched["matches"][0]["files"]["events"].endswith("data/events/100.json")
    assert fetched["matches"][0]["files"]["three_sixty"] is None


def test_status_for_missing_catalog(tmp_path: Path) -> None:
    assert read_catalog_status(tmp_path / "missing.sqlite") == {
        "exists": False,
        "stale": True,
    }
