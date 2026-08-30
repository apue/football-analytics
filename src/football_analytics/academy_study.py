"""Validated configuration for one repeatable academy-conversion study."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AcademyStudyConfig:
    """Research rules and reader-facing metadata frozen for one study."""

    study_id: str
    academy_id: str
    academy_display_name: str
    squad_name: str
    roster_season_start: int
    roster_season_end: int
    exit_season_start: int
    exit_season_end: int
    observation_season_count: int
    primary_appearance_threshold: int
    sensitivity_thresholds: tuple[int, ...]
    sustained_qualifying_seasons: int
    competition_policy_path: str
    roster_source_config_path: str
    roster_evidence_path: str
    roster_source_policy_status: str
    roster_source_public_url: str
    adult_source_scope_id: str
    adult_source_policy_status: str
    adult_source_public_url: str
    adult_source_coverage_note: str
    run_dir: str
    report_path: str

    def summary(self) -> dict[str, Any]:
        """Return the stable fields useful in validation and handoffs."""

        return {
            "study_id": self.study_id,
            "academy_id": self.academy_id,
            "squad_name": self.squad_name,
            "exit_seasons": [self.exit_season_start, self.exit_season_end],
            "observation_season_count": self.observation_season_count,
            "primary_threshold": self.primary_appearance_threshold,
            "thresholds": list(self.sensitivity_thresholds),
            "source_policy": {
                "roster_source": self.roster_source_policy_status,
                "adult_source": self.adult_source_policy_status,
            },
            "run_dir": self.run_dir,
            "report_path": self.report_path,
        }


def load_academy_study_config(path: Path) -> AcademyStudyConfig:
    """Load and validate one study JSON file."""

    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid study config {path}: {exc}") from exc
    root = _object(value, "study config")
    _only_fields(
        root,
        {
            "schema_version",
            "study_id",
            "academy",
            "cohorts",
            "outcomes",
            "roster_source",
            "adult_source",
            "outputs",
        },
        "study config",
    )

    if _integer(root.get("schema_version"), "schema_version") != 1:
        raise ValueError("schema_version must be 1")
    study_id = _text(root.get("study_id"), "study_id")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", study_id):
        raise ValueError("study_id must use lowercase letters, digits, and hyphens")

    academy = _object(root.get("academy"), "academy")
    _only_fields(academy, {"academy_id", "display_name", "squad_name"}, "academy")
    academy_id = _text(academy.get("academy_id"), "academy.academy_id")
    display_name = _text(academy.get("display_name"), "academy.display_name")
    squad_name = _text(academy.get("squad_name"), "academy.squad_name")

    cohorts = _object(root.get("cohorts"), "cohorts")
    _only_fields(
        cohorts,
        {
            "roster_season_start",
            "roster_season_end",
            "exit_season_start",
            "exit_season_end",
            "observation_season_count",
        },
        "cohorts",
    )
    roster_start = _integer(
        cohorts.get("roster_season_start"), "cohorts.roster_season_start"
    )
    roster_end = _integer(cohorts.get("roster_season_end"), "cohorts.roster_season_end")
    exit_start = _integer(cohorts.get("exit_season_start"), "cohorts.exit_season_start")
    exit_end = _integer(cohorts.get("exit_season_end"), "cohorts.exit_season_end")
    observation_count = _integer(
        cohorts.get("observation_season_count"),
        "cohorts.observation_season_count",
    )
    if not roster_start <= exit_start <= exit_end < roster_end:
        raise ValueError(
            "season order must satisfy roster_start <= exit_start "
            "<= exit_end < roster_end"
        )
    if observation_count < 1:
        raise ValueError("observation_season_count must be positive")

    outcomes = _object(root.get("outcomes"), "outcomes")
    _only_fields(
        outcomes,
        {
            "primary_appearance_threshold",
            "sensitivity_thresholds",
            "sustained_qualifying_seasons",
            "competition_policy_path",
        },
        "outcomes",
    )
    primary = _integer(
        outcomes.get("primary_appearance_threshold"),
        "outcomes.primary_appearance_threshold",
    )
    threshold_values = outcomes.get("sensitivity_thresholds")
    if not isinstance(threshold_values, list) or not threshold_values:
        raise ValueError("outcomes.sensitivity_thresholds must be a non-empty list")
    thresholds = tuple(
        _integer(item, "outcomes.sensitivity_thresholds[]") for item in threshold_values
    )
    if any(item < 1 for item in thresholds):
        raise ValueError("appearance thresholds must be positive")
    if primary not in thresholds:
        raise ValueError("primary threshold must appear in sensitivity thresholds")
    if len(set(thresholds)) != len(thresholds):
        raise ValueError("sensitivity thresholds must be unique")
    sustained = _integer(
        outcomes.get("sustained_qualifying_seasons"),
        "outcomes.sustained_qualifying_seasons",
    )
    if sustained < 2 or sustained > observation_count:
        raise ValueError(
            "sustained qualifying seasons must be between 2 and the observation count"
        )
    competition_policy_path = _text(
        outcomes.get("competition_policy_path"),
        "outcomes.competition_policy_path",
    )

    roster_source = _source(
        root.get("roster_source"),
        "roster_source",
        {"config_path", "evidence_path", "policy_status", "public_url"},
    )
    roster_config_path = _text(
        roster_source.get("config_path"), "roster_source.config_path"
    )
    roster_evidence_path = _text(
        roster_source.get("evidence_path"), "roster_source.evidence_path"
    )
    adult_source = _source(
        root.get("adult_source"),
        "adult_source",
        {"scope_id", "policy_status", "public_url", "coverage_note"},
    )
    adult_scope = _text(adult_source.get("scope_id"), "adult_source.scope_id")
    adult_coverage_note = _text(
        adult_source.get("coverage_note"), "adult_source.coverage_note"
    )

    outputs = _object(root.get("outputs"), "outputs")
    _only_fields(outputs, {"run_dir", "report_path"}, "outputs")
    run_dir = _text(outputs.get("run_dir"), "outputs.run_dir")
    report_path = _text(outputs.get("report_path"), "outputs.report_path")
    if not _is_within(Path(report_path), Path(run_dir)):
        raise ValueError("outputs.report_path must be inside outputs.run_dir")

    return AcademyStudyConfig(
        study_id=study_id,
        academy_id=academy_id,
        academy_display_name=display_name,
        squad_name=squad_name,
        roster_season_start=roster_start,
        roster_season_end=roster_end,
        exit_season_start=exit_start,
        exit_season_end=exit_end,
        observation_season_count=observation_count,
        primary_appearance_threshold=primary,
        sensitivity_thresholds=thresholds,
        sustained_qualifying_seasons=sustained,
        competition_policy_path=competition_policy_path,
        roster_source_config_path=roster_config_path,
        roster_evidence_path=roster_evidence_path,
        roster_source_policy_status=roster_source["policy_status"],
        roster_source_public_url=roster_source["public_url"],
        adult_source_scope_id=adult_scope,
        adult_source_policy_status=adult_source["policy_status"],
        adult_source_public_url=adult_source["public_url"],
        adult_source_coverage_note=adult_coverage_note,
        run_dir=run_dir,
        report_path=report_path,
    )


def _source(value: Any, name: str, fields: set[str]) -> dict[str, str]:
    source = _object(value, name)
    _only_fields(source, fields, name)
    status = _text(source.get("policy_status"), f"{name}.policy_status")
    if status != "approved":
        raise ValueError(f"{name}.policy_status must be approved")
    public_url = _text(source.get("public_url"), f"{name}.public_url")
    return {
        **source,
        "policy_status": status,
        "public_url": public_url,
    }


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _only_fields(value: dict[str, Any], fields: set[str], name: str) -> None:
    unsupported = sorted(set(value) - fields)
    if unsupported:
        raise ValueError(f"{name} has unsupported fields: {unsupported}")


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True
