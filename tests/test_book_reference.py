from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from football_analytics.book_reference import (
    BookReferenceError,
    BookReferenceSpec,
    load_reference_spec,
    reference_status,
    search_reference,
    show_reference,
    sync_reference,
)
from football_analytics.book_reference_cli import main

ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = ROOT / "scripts" / "sync_book_reference.sh"


def run(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def source_repository(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "source"
    source.mkdir()
    run("git", "init", "-b", "main", cwd=source)
    run("git", "config", "user.name", "Test User", cwd=source)
    run("git", "config", "user.email", "test@example.com", cwd=source)
    notebook_path = source / "extras" / "chapter-3" / "demo.ipynb"
    notebook_path.parent.mkdir(parents=True)
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "source": ["# Heatmap example\n", "Use a KDE for shape.\n"],
            },
            {
                "cell_type": "code",
                "source": ["pitch.kdeplot(x, y, levels=10)\n"],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    notebook_path.write_text(json.dumps(notebook), encoding="utf-8")
    (source / "README.md").write_text("Passing network reference\n", encoding="utf-8")
    run("git", "add", ".", cwd=source)
    run("git", "commit", "-m", "Add reference material", cwd=source)
    return source, run("git", "rev-parse", "HEAD", cwd=source)


def manifest(tmp_path: Path, source: Path, commit: str) -> Path:
    path = tmp_path / "sources.toml"
    path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[source.soccer_analytics_ml]",
                'name = "Test book"',
                f'url = "{source}"',
                f'commit = "{commit}"',
                'checkout = "test-book"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def synced_reference(
    tmp_path: Path,
) -> tuple[Path, Path, BookReferenceSpec]:
    source, commit = source_repository(tmp_path)
    manifest_path = manifest(tmp_path, source, commit)
    spec = load_reference_spec(manifest_path)
    repository = tmp_path / "external" / "book"
    sync_reference(repository, spec)
    return repository, manifest_path, spec


def test_sync_materializes_exact_pin_and_never_follows_new_source_commit(
    tmp_path: Path,
) -> None:
    source, pinned_commit = source_repository(tmp_path)
    manifest_path = manifest(tmp_path, source, pinned_commit)
    spec = load_reference_spec(manifest_path)
    repository = tmp_path / "external" / "book"

    status = sync_reference(repository, spec)
    assert status["ready"] is True
    assert status["current_commit"] == pinned_commit

    (source / "README.md").write_text("Changed upstream\n", encoding="utf-8")
    run("git", "add", "README.md", cwd=source)
    run("git", "commit", "-m", "Move upstream", cwd=source)

    second_status = sync_reference(repository, spec)
    assert second_status["current_commit"] == pinned_commit
    assert (repository / "README.md").read_text() == "Passing network reference\n"


def test_sync_refuses_to_replace_a_non_git_path(tmp_path: Path) -> None:
    source, pinned_commit = source_repository(tmp_path)
    spec = load_reference_spec(manifest(tmp_path, source, pinned_commit))
    repository = tmp_path / "external" / "book"
    repository.mkdir(parents=True)
    (repository / "learner-note.txt").write_text("preserve me\n")

    with pytest.raises(BookReferenceError, match="Refusing to replace non-Git"):
        sync_reference(repository, spec)

    assert (repository / "learner-note.txt").read_text() == "preserve me\n"


def test_sync_script_works_outside_the_project_directory(tmp_path: Path) -> None:
    source, pinned_commit = source_repository(tmp_path)
    manifest_path = manifest(tmp_path, source, pinned_commit)
    repository = tmp_path / "script-book"

    subprocess.run(
        [
            SYNC_SCRIPT,
            "--repository",
            str(repository),
            "--manifest",
            str(manifest_path),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert run("git", "rev-parse", "HEAD", cwd=repository) == pinned_commit


def test_search_and_show_return_notebook_cell_locations(tmp_path: Path) -> None:
    repository, _, spec = synced_reference(tmp_path)

    matches = search_reference(repository, spec, "kdeplot", chapter="3")
    assert matches == [
        {
            "path": "extras/chapter-3/demo.ipynb",
            "cell": 1,
            "cell_type": "code",
            "line": 1,
            "snippet": "pitch.kdeplot(x, y, levels=10)",
        }
    ]
    assert search_reference(repository, spec, "kdeplot", chapter="4") == []

    result = show_reference(
        repository,
        spec,
        "extras/chapter-3/demo.ipynb",
        cell=1,
    )
    assert result["cell_type"] == "code"
    assert result["content"] == "pitch.kdeplot(x, y, levels=10)\n"


def test_queries_reject_dirty_wrong_source_and_escaping_paths(tmp_path: Path) -> None:
    repository, _, spec = synced_reference(tmp_path)
    (repository / "README.md").write_text("local edit\n", encoding="utf-8")

    assert reference_status(repository, spec)["state"] == "dirty"
    with pytest.raises(BookReferenceError, match="not ready \\(dirty\\)"):
        search_reference(repository, spec, "network")
    with pytest.raises(BookReferenceError, match="local changes"):
        sync_reference(repository, spec)

    run("git", "checkout", "--", "README.md", cwd=repository)
    with pytest.raises(BookReferenceError, match="escapes"):
        show_reference(repository, spec, "../outside.md")

    run("git", "remote", "set-url", "origin", str(tmp_path / "other"), cwd=repository)
    assert reference_status(repository, spec)["state"] == "source_mismatch"
    with pytest.raises(BookReferenceError, match="source_mismatch"):
        search_reference(repository, spec, "network")


def test_cli_status_does_not_materialize_a_missing_repository(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source, commit = source_repository(tmp_path)
    manifest_path = manifest(tmp_path, source, commit)
    repository = tmp_path / "missing-book"

    assert (
        main(
            [
                "--repository",
                str(repository),
                "--manifest",
                str(manifest_path),
                "status",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["reference"]["state"] == "missing"
    assert not repository.exists()


def test_cli_emits_stable_json_for_status_search_and_show(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, manifest_path, _ = synced_reference(tmp_path)
    common = [
        "--repository",
        str(repository),
        "--manifest",
        str(manifest_path),
    ]

    assert main([*common, "status"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["reference"]["ready"] is True

    assert main([*common, "search", "heatmap", "--chapter", "3"]) == 0
    search = json.loads(capsys.readouterr().out)
    assert search["matches"][0]["cell"] == 0

    assert main([*common, "show", "README.md"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["result"]["content"] == "Passing network reference\n"


def test_manifest_requires_a_full_commit(tmp_path: Path) -> None:
    source, _ = source_repository(tmp_path)
    manifest_path = manifest(tmp_path, source, "abc123")

    with pytest.raises(BookReferenceError, match="40-character"):
        load_reference_spec(manifest_path)


def test_manifest_requires_a_source_table(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sources.toml"
    manifest_path.write_text("schema_version = 1\nsource = []\n")

    with pytest.raises(BookReferenceError, match="source table"):
        load_reference_spec(manifest_path)
