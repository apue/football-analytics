"""Project and source-data path resolution."""

from __future__ import annotations

import os
from pathlib import Path

OPEN_DATA_ENV = "STATSBOMB_OPEN_DATA"


def get_project_root(start: Path | None = None) -> Path:
    """Find the nearest parent containing this project's pyproject file."""
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        pyproject = candidate / "pyproject.toml"
        is_project = (
            pyproject.is_file()
            and 'name = "football-analytics"' in pyproject.read_text()
        )
        if is_project:
            return candidate

    raise FileNotFoundError(
        "Could not find the football-analytics project root from "
        f"{current}. Run inside the repository."
    )


def get_open_data_root(project_root: Path | None = None) -> Path:
    """Return the configured Hudl StatsBomb open-data repository path."""
    override = os.getenv(OPEN_DATA_ENV)
    if override:
        return Path(override).expanduser().resolve()

    root = project_root.resolve() if project_root else get_project_root()
    return root / "data" / "external" / "statsbomb-open-data"
