from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync_open_data.sh"


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def make_source_repository(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    run("git", "init", "-b", "main", cwd=source)
    run("git", "config", "user.name", "Test User", cwd=source)
    run("git", "config", "user.email", "test@example.com", cwd=source)
    (source / "data").mkdir()
    (source / "data" / "competitions.json").write_text("[]\n")
    (source / "data" / "matches" / "1").mkdir(parents=True)
    (source / "data" / "matches" / "1" / "2.json").write_text("[]\n")
    (source / "data" / "events").mkdir()
    (source / "data" / "events" / "large.json").write_text("not checked out\n")
    run("git", "add", "data", cwd=source)
    run("git", "commit", "-m", "Initial test data", cwd=source)
    return source


def sync_environment(data_root: Path, source: Path) -> dict[str, str]:
    return {
        **os.environ,
        "FOOTBALL_ANALYTICS_DATA_ROOT": str(data_root),
        "FOOTBALL_ANALYTICS_OPEN_DATA_URL": str(source),
    }


def test_sync_clones_then_updates_existing_repository(tmp_path: Path) -> None:
    source = make_source_repository(tmp_path)
    data_root = tmp_path / "external"
    environment = sync_environment(data_root, source)

    subprocess.run([SCRIPT], check=True, env=environment, capture_output=True)
    clone = data_root / "statsbomb-open-data"
    assert (clone / "data" / "competitions.json").is_file()
    assert (clone / "data" / "matches" / "1" / "2.json").is_file()
    assert not (clone / "data" / "events").exists()

    expected = '[{"competition_id": 1}]\n'
    (source / "data" / "competitions.json").write_text(expected)
    run("git", "add", "data/competitions.json", cwd=source)
    run("git", "commit", "-m", "Update test data", cwd=source)

    subprocess.run([SCRIPT], check=True, env=environment, capture_output=True)
    assert (clone / "data" / "competitions.json").read_text() == expected
    assert not list(data_root.glob(".open-data-clone.*"))


def test_failed_clone_cleans_temporary_directory(tmp_path: Path) -> None:
    data_root = tmp_path / "external"
    missing_source = tmp_path / "missing"
    environment = sync_environment(data_root, missing_source)

    result = subprocess.run([SCRIPT], env=environment, capture_output=True)

    assert result.returncode != 0
    assert not (data_root / "statsbomb-open-data").exists()
    assert not list(data_root.glob(".open-data-clone.*"))
