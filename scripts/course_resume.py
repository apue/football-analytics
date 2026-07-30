#!/usr/bin/env python3
"""Print a read-only course recovery summary for learner confirmation."""

from __future__ import annotations

import argparse
from pathlib import Path

from football_analytics.course_progress import (
    build_resume_summary,
    render_resume_summary,
)
from football_analytics.paths import get_project_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root; defaults to the current football-analytics project.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve() if args.root else get_project_root()
    summary = build_resume_summary(root)
    print(render_resume_summary(summary))
    return 0 if summary.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
