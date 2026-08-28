#!/usr/bin/env python3
"""Validate the reusable academy-conversion study request contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def validate_study_config(
    value: dict[str, Any], *, require_approved: bool = False
) -> dict[str, Any]:
    """Return a concise validated summary or raise ``ValueError``."""

    if _integer(value.get("schema_version"), "schema_version") != 1:
        raise ValueError("schema_version must be 1")
    study_id = _text(value.get("study_id"), "study_id")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", study_id):
        raise ValueError("study_id must use lowercase letters, digits, and hyphens")

    academy = _object(value.get("academy"), "academy")
    for field in ("academy_id", "display_name", "squad_name"):
        _text(academy.get(field), f"academy.{field}")

    cohorts = _object(value.get("cohorts"), "cohorts")
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

    outcomes = _object(value.get("outcomes"), "outcomes")
    primary = _integer(
        outcomes.get("primary_appearance_threshold"),
        "outcomes.primary_appearance_threshold",
    )
    thresholds = outcomes.get("sensitivity_thresholds")
    if not isinstance(thresholds, list) or not thresholds:
        raise ValueError("outcomes.sensitivity_thresholds must be a non-empty list")
    normalized_thresholds = [
        _integer(item, "outcomes.sensitivity_thresholds[]") for item in thresholds
    ]
    if any(item < 1 for item in normalized_thresholds):
        raise ValueError("appearance thresholds must be positive")
    if primary not in normalized_thresholds:
        raise ValueError("primary threshold must appear in sensitivity thresholds")
    if len(set(normalized_thresholds)) != len(normalized_thresholds):
        raise ValueError("sensitivity thresholds must be unique")
    sustained = _integer(
        outcomes.get("sustained_qualifying_seasons"),
        "outcomes.sustained_qualifying_seasons",
    )
    if sustained < 2 or sustained > observation_count:
        raise ValueError(
            "sustained qualifying seasons must be between 2 and the observation count"
        )
    _text(
        outcomes.get("competition_policy_path"),
        "outcomes.competition_policy_path",
    )

    policy_states = {}
    for section_name in ("roster_source", "adult_source"):
        section = _object(value.get(section_name), section_name)
        _text(section.get("adapter"), f"{section_name}.adapter")
        required_detail = (
            "config_path" if section_name == "roster_source" else "scope_id"
        )
        _text(section.get(required_detail), f"{section_name}.{required_detail}")
        status = _text(section.get("policy_status"), f"{section_name}.policy_status")
        if status not in {"pending", "approved", "prohibited"}:
            raise ValueError(
                f"{section_name}.policy_status must be pending, approved, or prohibited"
            )
        if require_approved and status != "approved":
            raise ValueError(
                f"{section_name}.policy_status must be approved before acquisition"
            )
        policy_states[section_name] = status

    outputs = _object(value.get("outputs"), "outputs")
    for field in ("run_dir", "report_path", "language"):
        _text(outputs.get(field), f"outputs.{field}")

    return {
        "study_id": study_id,
        "academy_id": academy["academy_id"],
        "squad_name": academy["squad_name"],
        "exit_seasons": [exit_start, exit_end],
        "observation_season_count": observation_count,
        "primary_threshold": primary,
        "thresholds": normalized_thresholds,
        "source_policy": policy_states,
        "report_path": outputs["report_path"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args()
    try:
        value = json.loads(args.config.read_text())
        summary = validate_study_config(
            _object(value, "study config"), require_approved=args.require_approved
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
