#!/usr/bin/env python3
"""Validate one academy-conversion study request through the core package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from football_analytics.academy_study import load_academy_study_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args()
    try:
        study = load_academy_study_config(
            args.config, require_approved=args.require_approved
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(study.summary(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
