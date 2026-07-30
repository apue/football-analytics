from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from football_analytics.course_progress import (
    ALLOWED_LESSON_STATUSES,
    build_resume_summary,
    render_resume_summary,
    validate_course,
)


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def write_course(
    root: Path,
    *,
    state_lesson: str = "00-01-orientation",
    handoff_lesson: str = "00-01-orientation",
    status: str = "in_progress",
    checkpoint_id: str = "CP-001",
) -> Path:
    lesson_dir = root / "course" / "lessons" / state_lesson
    lesson_dir.mkdir(parents=True)
    (lesson_dir / "brief.md").write_text("# Brief\n")
    (root / "course" / "templates").mkdir(parents=True)
    for name in {
        "analysis.ipynb",
        "brief.md",
        "checks.md",
        "exercises.md",
        "findings.md",
        "handoff.md",
    }:
        (root / "course" / "templates" / name).write_text("")

    state = {
        "schema_version": 2,
        "current_stage": 0,
        "current_lesson": state_lesson,
        "completed_lessons": ([state_lesson] if status == "completed" else []),
        "updated_at": "2026-07-30T10:00:00+08:00",
    }
    (root / "course" / "state.yaml").write_text(yaml.safe_dump(state, sort_keys=False))
    (lesson_dir / "handoff.md").write_text(
        f"""---
lesson_id: {handoff_lesson}
stage: 0
status: {status}
checkpoint_id: {checkpoint_id}
current_step: Inspect the available event data
next_action: Propose one match for learner review
updated_at: 2026-07-30T10:00:00+08:00
---

# Handoff

## Completed

- Course contract initialized.

## Current Work

- Data coverage inspection has started.

## Decisions

- Prefer a match with events, lineups, and 360 data.

## Validation

- `uv run pytest`: not run for this learning unit.

## Open Questions

- Which match is clearest for orientation?

## Checkpoint History

- {checkpoint_id} | 2026-07-30T10:00:00+08:00 | {status} | Inspect data coverage
"""
    )
    return lesson_dir


def initialize_git(root: Path, *, checkpoint_subject: str | None) -> None:
    run_git(root, "init", "-b", "lesson/00-01-orientation")
    run_git(root, "config", "user.name", "Test Agent")
    run_git(root, "config", "user.email", "agent@example.com")
    run_git(root, "add", ".")
    subject = checkpoint_subject or "chore: initialize test repository"
    run_git(root, "commit", "-m", subject)


@pytest.mark.parametrize("status", sorted(ALLOWED_LESSON_STATUSES))
def test_resume_supports_every_lesson_status(tmp_path: Path, status: str) -> None:
    write_course(tmp_path, status=status)
    initialize_git(
        tmp_path,
        checkpoint_subject=(
            "checkpoint(00-01-orientation): CP-001 inspect data coverage"
        ),
    )

    summary = build_resume_summary(tmp_path)

    assert summary.status == status
    assert summary.is_valid
    assert summary.worktree_state == "clean"
    assert summary.checkpoint_commit_exists
    assert summary.checkpoint_matches_latest


def test_resume_labels_uncommitted_work_after_checkpoint(tmp_path: Path) -> None:
    lesson_dir = write_course(tmp_path)
    initialize_git(
        tmp_path,
        checkpoint_subject=(
            "checkpoint(00-01-orientation): CP-001 inspect data coverage"
        ),
    )
    (lesson_dir / "notes.txt").write_text("unfinished learner notes\n")

    summary = build_resume_summary(tmp_path)
    rendered = render_resume_summary(summary)

    assert summary.is_valid
    assert summary.worktree_state == "dirty"
    assert "post-checkpoint uncommitted work" in rendered
    assert any(path.endswith("notes.txt") for path in summary.changed_paths)


def test_resume_cli_prints_clean_checkpoint_summary(tmp_path: Path) -> None:
    write_course(tmp_path, status="ready", checkpoint_id="CP-000")
    initialize_git(
        tmp_path,
        checkpoint_subject=("checkpoint(00-01-orientation): CP-000 initialize lesson"),
    )
    script = Path(__file__).parents[1] / "scripts" / "course_resume.py"

    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Checkpoint commit exists: yes" in result.stdout
    assert "Worktree: clean" in result.stdout
    assert "Await learner confirmation before continuing." in result.stdout


def test_resume_rejects_handoff_and_global_lesson_mismatch(tmp_path: Path) -> None:
    write_course(tmp_path, state_lesson="00-02-event-table")
    initialize_git(
        tmp_path,
        checkpoint_subject=(
            "checkpoint(00-01-orientation): CP-001 inspect data coverage"
        ),
    )

    summary = build_resume_summary(tmp_path)

    assert not summary.is_valid
    assert any(
        "Handoff lesson_id does not match global current_lesson" in error
        for error in summary.errors
    )


def test_resume_reports_missing_checkpoint_commit(tmp_path: Path) -> None:
    write_course(tmp_path)
    initialize_git(tmp_path, checkpoint_subject=None)

    summary = build_resume_summary(tmp_path)

    assert not summary.is_valid
    assert not summary.checkpoint_commit_exists
    assert any("checkpoint commit not found" in error for error in summary.errors)


def test_resume_reports_latest_checkpoint_id_mismatch(tmp_path: Path) -> None:
    write_course(tmp_path, checkpoint_id="CP-002")
    initialize_git(
        tmp_path,
        checkpoint_subject=(
            "checkpoint(00-01-orientation): CP-001 inspect data coverage"
        ),
    )

    summary = build_resume_summary(tmp_path)

    assert not summary.is_valid
    assert not summary.checkpoint_commit_exists
    assert summary.latest_checkpoint_id == "CP-001"
    assert any("latest Git checkpoint is CP-001" in error for error in summary.errors)


def test_validate_course_checks_state_v2_and_handoff_contract(tmp_path: Path) -> None:
    lesson_dir = write_course(tmp_path)

    assert validate_course(tmp_path) == []

    state_path = tmp_path / "course" / "state.yaml"
    state = yaml.safe_load(state_path.read_text())
    state["schema_version"] = 1
    state["next_action"] = "duplicate"
    state_path.write_text(yaml.safe_dump(state, sort_keys=False))
    handoff_path = lesson_dir / "handoff.md"
    handoff_path.write_text(
        handoff_path.read_text().replace(
            "- CP-001 | 2026-07-30T10:00:00+08:00 | in_progress",
            "- CP-000 | 2026-07-30T10:00:00+08:00 | in_progress",
        )
    )

    errors = validate_course(tmp_path)

    assert any("schema_version must be 2" in error for error in errors)
    assert any("retired keys" in error for error in errors)
    assert any("latest checkpoint history entry" in error for error in errors)


def test_validate_course_rejects_invalid_handoff_fields(tmp_path: Path) -> None:
    lesson_dir = write_course(tmp_path)
    handoff_path = lesson_dir / "handoff.md"
    handoff_path.write_text(
        handoff_path.read_text()
        .replace("checkpoint_id: CP-001", "checkpoint_id: checkpoint-1")
        .replace(
            "next_action: Propose one match for learner review",
            "next_action: ''",
        )
    )

    errors = validate_course(tmp_path)

    assert any("checkpoint_id must match CP-NNN" in error for error in errors)
    assert any("next_action must be non-empty" in error for error in errors)
