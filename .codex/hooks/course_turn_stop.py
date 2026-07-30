#!/usr/bin/env python3
"""Ask Codex to review a dirty worktree once before ending a turn."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    payload = json.load(sys.stdin)
    cwd = Path(payload["cwd"])
    if payload.get("stop_hook_active"):
        return 0

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if status.returncode != 0 or not status.stdout.strip():
        return 0

    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    "The worktree is dirty. Use $course-turn-checkpoint "
                    "before finishing this turn."
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
