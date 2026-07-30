from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from football_analytics.course_progress import (
    build_resume_summary,
    render_resume_summary,
    validate_course,
)


def run_git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def make_course(root: Path, *, checkpoint_commit: bool = True) -> Path:
    lesson_id = "00-01-orientation"
    lesson_dir = root / "course" / "lessons" / lesson_id
    lesson_dir.mkdir(parents=True)
    (lesson_dir / "brief.md").write_text("# Brief\n")
    state = {
        "schema_version": 2,
        "current_stage": 0,
        "current_lesson": lesson_id,
        "completed_lessons": [],
        "updated_at": "2026-07-30T10:00:00+08:00",
    }
    (root / "course" / "state.yaml").write_text(yaml.safe_dump(state, sort_keys=False))
    handoff = """---
lesson_id: 00-01-orientation
status: ready
checkpoint_id: CP-000
current_step: Confirm the lesson starting point
next_action: Inspect available data coverage
updated_at: 2026-07-30T10:00:00+08:00
---

# Handoff
"""
    (lesson_dir / "handoff.md").write_text(handoff)

    run_git(root, "init", "-b", "lesson/00-01-orientation")
    run_git(root, "config", "user.name", "Test Agent")
    run_git(root, "config", "user.email", "agent@example.com")
    run_git(root, "add", ".")
    subject = (
        "checkpoint(00-01-orientation): CP-000 initialize lesson"
        if checkpoint_commit
        else "chore: initialize repository"
    )
    run_git(root, "commit", "-m", subject)
    return lesson_dir


def test_resume_cli_reports_clean_reachable_checkpoint(tmp_path: Path) -> None:
    make_course(tmp_path)
    script = Path(__file__).parents[1] / "scripts" / "course_resume.py"

    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Checkpoint commit: not found" not in result.stdout
    assert "Worktree: clean" in result.stdout
    assert "Warnings:" not in result.stdout


def test_resume_reports_uncommitted_work(tmp_path: Path) -> None:
    lesson_dir = make_course(tmp_path)
    (lesson_dir / "notes.txt").write_text("unfinished\n")

    summary = build_resume_summary(tmp_path)

    assert summary.is_valid
    assert summary.worktree_state == "dirty"
    assert any("uncommitted work" in warning for warning in summary.warnings)
    assert any(path.endswith("notes.txt") for path in summary.changed_paths)


def test_unreachable_checkpoint_is_a_warning_not_an_error(tmp_path: Path) -> None:
    make_course(tmp_path, checkpoint_commit=False)
    run_git(tmp_path, "switch", "-c", "archived-checkpoint")
    run_git(
        tmp_path,
        "commit",
        "--allow-empty",
        "-m",
        "checkpoint(00-01-orientation): CP-000 archived lesson",
    )
    run_git(tmp_path, "switch", "lesson/00-01-orientation")

    summary = build_resume_summary(tmp_path)

    assert summary.is_valid
    assert summary.checkpoint_commit is None
    assert any("No reachable checkpoint" in warning for warning in summary.warnings)


def test_invalid_state_is_a_clear_error(tmp_path: Path) -> None:
    make_course(tmp_path)
    (tmp_path / "course" / "state.yaml").write_text("schema_version: 1\n")

    summary = build_resume_summary(tmp_path)
    rendered = render_resume_summary(summary)

    assert not summary.is_valid
    assert "Course state missing fields" in rendered
    assert "schema_version must be 2" in rendered


def test_course_validation_checks_active_lesson_identity(tmp_path: Path) -> None:
    lesson_dir = make_course(tmp_path)
    handoff_path = lesson_dir / "handoff.md"
    handoff_path.write_text(
        handoff_path.read_text().replace(
            "lesson_id: 00-01-orientation",
            "lesson_id: 00-02-event-table",
        )
    )

    errors = validate_course(tmp_path)

    assert "Lesson handoff lesson_id does not match current_lesson" in errors
