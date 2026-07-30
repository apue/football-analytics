from pathlib import Path

import pytest

from football_analytics.paths import (
    CATALOG_ENV,
    OPEN_DATA_ENV,
    get_catalog_path,
    get_open_data_root,
    get_project_root,
)


def test_get_project_root_from_nested_directory(tmp_path: Path) -> None:
    project = tmp_path / "project"
    nested = project / "course" / "lessons"
    nested.mkdir(parents=True)
    (project / "pyproject.toml").write_text('[project]\nname = "football-analytics"\n')

    assert get_project_root(nested) == project


def test_get_project_root_rejects_unrelated_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="project root"):
        get_project_root(tmp_path)


def test_open_data_root_uses_environment_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = tmp_path / "custom-open-data"
    monkeypatch.setenv(OPEN_DATA_ENV, str(expected))

    assert get_open_data_root() == expected


def test_open_data_root_uses_project_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(OPEN_DATA_ENV, raising=False)

    assert get_open_data_root(tmp_path) == (
        tmp_path / "data" / "external" / "statsbomb-open-data"
    )


def test_catalog_path_uses_environment_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = tmp_path / "catalog.sqlite"
    monkeypatch.setenv(CATALOG_ENV, str(expected))

    assert get_catalog_path() == expected


def test_catalog_path_uses_project_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(CATALOG_ENV, raising=False)

    assert get_catalog_path(tmp_path) == (
        tmp_path / "data" / "processed" / "open_data_catalog.sqlite"
    )
