#!/usr/bin/env python3
"""Validate the durable course state and lesson artifact contract."""

from __future__ import annotations

from football_analytics.course_progress import validate_course
from football_analytics.paths import get_project_root


def main() -> int:
    errors = validate_course(get_project_root())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Course state and active lesson metadata are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
