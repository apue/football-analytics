#!/usr/bin/env python3
"""Validate the durable course state and lesson artifact contract."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "course" / "state.yaml"
REQUIRED_STATE_KEYS = {
    "schema_version",
    "current_stage",
    "current_lesson",
    "status",
    "completed_lessons",
    "next_action",
    "open_questions",
    "last_updated",
}
ALLOWED_STATUSES = {"ready", "in_progress", "blocked", "review", "completed"}
REQUIRED_TEMPLATES = {
    "analysis.ipynb",
    "brief.md",
    "checks.md",
    "exercises.md",
    "findings.md",
    "handoff.md",
}


def validate() -> list[str]:
    errors: list[str] = []
    if not STATE_PATH.is_file():
        return [f"Missing course state: {STATE_PATH.relative_to(ROOT)}"]

    state = yaml.safe_load(STATE_PATH.read_text()) or {}
    missing_keys = REQUIRED_STATE_KEYS - state.keys()
    if missing_keys:
        errors.append(f"Course state missing keys: {sorted(missing_keys)}")

    if state.get("status") not in ALLOWED_STATUSES:
        errors.append(f"Invalid course status: {state.get('status')!r}")

    lesson_id = state.get("current_lesson")
    if lesson_id:
        lesson_dir = ROOT / "course" / "lessons" / str(lesson_id)
        if not lesson_dir.is_dir():
            errors.append(f"Current lesson directory does not exist: {lesson_id}")
        else:
            for required in ("brief.md", "handoff.md"):
                if not (lesson_dir / required).is_file():
                    errors.append(f"Current lesson missing {required}: {lesson_id}")

    template_dir = ROOT / "course" / "templates"
    actual_templates = {path.name for path in template_dir.iterdir() if path.is_file()}
    missing_templates = REQUIRED_TEMPLATES - actual_templates
    if missing_templates:
        errors.append(f"Missing course templates: {sorted(missing_templates)}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Course state and templates are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
