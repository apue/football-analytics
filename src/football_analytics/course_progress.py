"""Minimal course state and read-only resume inspection."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

STATE_PATH = Path("course/state.yaml")
STATE_FIELDS = {
    "schema_version",
    "current_stage",
    "current_lesson",
    "completed_lessons",
    "updated_at",
}
HANDOFF_FIELDS = {
    "lesson_id",
    "status",
    "checkpoint_id",
    "current_step",
    "next_action",
    "updated_at",
}
LESSON_STATUSES = {
    "ready",
    "in_progress",
    "paused",
    "review",
    "completed",
    "blocked",
}
CHECKPOINT_ID = re.compile(r"^CP-\d{3}$")
CHECKPOINT_SUBJECT = re.compile(
    r"^checkpoint\((?P<lesson>[^)]+)\): "
    r"(?P<checkpoint>CP-\d{3}) (?P<step>.+)$"
)


@dataclass(frozen=True)
class CourseSnapshot:
    """The small machine-readable snapshot needed to resume a lesson."""

    stage: int
    lesson_id: str
    completed_lessons: tuple[str, ...]
    status: str
    checkpoint_id: str
    current_step: str
    next_action: str
    updated_at: str


@dataclass(frozen=True)
class ResumeSummary:
    """Learner-facing recovery information gathered without mutation."""

    snapshot: CourseSnapshot | None
    branch: str | None
    worktree_state: str
    changed_paths: tuple[str, ...]
    checkpoint_commit: str | None
    latest_checkpoint_id: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        """Whether the core state and Git repository were readable."""

        return not self.errors


def _read_yaml_mapping(path: Path, label: str) -> tuple[dict[str, Any], list[str]]:
    try:
        value = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as error:
        return {}, [f"Could not read {label}: {error}"]
    if not isinstance(value, dict):
        return {}, [f"{label} must contain a YAML mapping"]
    return value, []


def _is_timestamp(value: object) -> bool:
    if isinstance(value, (date, datetime)):
        return True
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            return False


def _read_handoff_frontmatter(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        text = path.read_text()
    except OSError as error:
        return {}, [f"Could not read lesson handoff: {error}"]
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if match is None:
        return {}, [f"Lesson handoff has no YAML frontmatter: {path}"]
    try:
        value = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        return {}, [f"Invalid lesson handoff frontmatter: {error}"]
    if not isinstance(value, dict):
        return {}, ["Lesson handoff frontmatter must be a YAML mapping"]
    return value, []


def _validate_fields(
    value: dict[str, Any], expected: set[str], label: str
) -> list[str]:
    errors: list[str] = []
    missing = expected - value.keys()
    unexpected = value.keys() - expected
    if missing:
        errors.append(f"{label} missing fields: {sorted(missing)}")
    if unexpected:
        errors.append(f"{label} has unexpected fields: {sorted(unexpected)}")
    return errors


def load_course_snapshot(root: Path) -> tuple[CourseSnapshot | None, list[str]]:
    """Load and validate the navigation state and active handoff frontmatter."""

    root = root.resolve()
    state, errors = _read_yaml_mapping(root / STATE_PATH, "course state")
    errors.extend(_validate_fields(state, STATE_FIELDS, "Course state"))

    if state.get("schema_version") != 2:
        errors.append("Course state schema_version must be 2")
    stage = state.get("current_stage")
    if not isinstance(stage, int) or isinstance(stage, bool) or stage < 0:
        errors.append("Course state current_stage must be a non-negative integer")
    lesson_id = state.get("current_lesson")
    if not isinstance(lesson_id, str) or not lesson_id.strip():
        errors.append("Course state current_lesson must be non-empty")
    completed = state.get("completed_lessons")
    if not isinstance(completed, list) or not all(
        isinstance(item, str) and item for item in completed
    ):
        errors.append("Course state completed_lessons must be a list of lesson IDs")
    if not _is_timestamp(state.get("updated_at")):
        errors.append("Course state updated_at must be an ISO date or timestamp")
    if errors:
        return None, errors

    handoff_path = root / "course" / "lessons" / lesson_id / "handoff.md"
    handoff, handoff_errors = _read_handoff_frontmatter(handoff_path)
    errors.extend(handoff_errors)
    errors.extend(_validate_fields(handoff, HANDOFF_FIELDS, "Lesson handoff"))
    if handoff.get("lesson_id") != lesson_id:
        errors.append("Lesson handoff lesson_id does not match current_lesson")
    status = handoff.get("status")
    if status not in LESSON_STATUSES:
        errors.append(f"Invalid lesson status: {status!r}")
    checkpoint_id = handoff.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not CHECKPOINT_ID.fullmatch(checkpoint_id):
        errors.append("Lesson handoff checkpoint_id must match CP-NNN")
    for field in ("current_step", "next_action"):
        field_value = handoff.get(field)
        if not isinstance(field_value, str) or not field_value.strip():
            errors.append(f"Lesson handoff {field} must be non-empty")
    if not _is_timestamp(handoff.get("updated_at")):
        errors.append("Lesson handoff updated_at must be an ISO date or timestamp")
    if errors:
        return None, errors

    return (
        CourseSnapshot(
            stage=stage,
            lesson_id=lesson_id,
            completed_lessons=tuple(completed),
            status=status,
            checkpoint_id=checkpoint_id,
            current_step=handoff["current_step"],
            next_action=handoff["next_action"],
            updated_at=str(handoff["updated_at"]),
        ),
        [],
    )


def validate_course(root: Path) -> list[str]:
    """Validate the navigation state and active lesson's required files."""

    snapshot, errors = load_course_snapshot(root)
    if snapshot is None:
        return errors

    lesson_dir = root.resolve() / "course" / "lessons" / snapshot.lesson_id
    if not (lesson_dir / "brief.md").is_file():
        errors.append(f"Current lesson missing brief.md: {snapshot.lesson_id}")
    is_completed = snapshot.status == "completed"
    is_listed = snapshot.lesson_id in snapshot.completed_lessons
    if is_completed != is_listed:
        errors.append("Current lesson status and completed_lessons disagree")
    return errors


def _run_git(root: Path, *args: str) -> tuple[str, str | None]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        return "", f"Git command failed ({' '.join(args)}): {detail}"
    return result.stdout, None


def _reachable_checkpoints(
    root: Path, lesson_id: str
) -> tuple[list[tuple[str, str]], str | None]:
    output, error = _run_git(root, "log", "HEAD", "--format=%H%x00%s")
    if error is not None:
        return [], error
    checkpoints: list[tuple[str, str]] = []
    for line in output.splitlines():
        commit_hash, separator, subject = line.partition("\0")
        if not separator:
            continue
        match = CHECKPOINT_SUBJECT.fullmatch(subject)
        if match is not None and match.group("lesson") == lesson_id:
            checkpoints.append((commit_hash, match.group("checkpoint")))
    return checkpoints, None


def build_resume_summary(root: Path) -> ResumeSummary:
    """Inspect the current course and Git state without changing either."""

    root = root.resolve()
    snapshot, errors = load_course_snapshot(root)
    warnings: list[str] = []

    branch_output, branch_error = _run_git(root, "branch", "--show-current")
    if branch_error:
        errors.append(branch_error)
    branch = branch_output.strip() or None

    status_output, status_error = _run_git(root, "status", "--porcelain")
    if status_error:
        errors.append(status_error)
    changed_paths = tuple(
        line[3:] for line in status_output.splitlines() if len(line) >= 4
    )
    worktree_state = "dirty" if changed_paths else "clean"
    if changed_paths:
        warnings.append("Post-checkpoint uncommitted work requires review")

    checkpoint_commit: str | None = None
    latest_checkpoint_id: str | None = None
    if snapshot is not None:
        expected_branch = f"lesson/{snapshot.lesson_id}"
        if snapshot.status != "completed" and branch != expected_branch:
            warnings.append(
                f"Expected branch {expected_branch}, found {branch or 'detached HEAD'}"
            )
        checkpoints, checkpoint_error = _reachable_checkpoints(root, snapshot.lesson_id)
        if checkpoint_error:
            errors.append(checkpoint_error)
        elif not checkpoints:
            warnings.append(f"No reachable checkpoint commit for {snapshot.lesson_id}")
        else:
            latest_commit, latest_checkpoint_id = checkpoints[0]
            matching = [
                commit_hash
                for commit_hash, checkpoint_id in checkpoints
                if checkpoint_id == snapshot.checkpoint_id
            ]
            if matching:
                checkpoint_commit = matching[0]
            if latest_checkpoint_id != snapshot.checkpoint_id:
                warnings.append(
                    f"Handoff checkpoint is {snapshot.checkpoint_id}, "
                    f"latest reachable checkpoint is {latest_checkpoint_id}"
                )
            elif checkpoint_commit is None:
                checkpoint_commit = latest_commit

    return ResumeSummary(
        snapshot=snapshot,
        branch=branch,
        worktree_state=worktree_state,
        changed_paths=changed_paths,
        checkpoint_commit=checkpoint_commit,
        latest_checkpoint_id=latest_checkpoint_id,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def render_resume_summary(summary: ResumeSummary) -> str:
    """Render a concise recovery summary for learner confirmation."""

    snapshot = summary.snapshot
    checkpoint_commit = (
        summary.checkpoint_commit[:12] if summary.checkpoint_commit else "not found"
    )
    lines = [
        "Course resume summary",
        f"Lesson: {snapshot.lesson_id if snapshot else 'unknown'}",
        f"Stage: {snapshot.stage if snapshot else 'unknown'}",
        f"Status: {snapshot.status if snapshot else 'unknown'}",
        f"Checkpoint: {snapshot.checkpoint_id if snapshot else 'unknown'}",
        f"Checkpoint commit: {checkpoint_commit}",
        f"Current step: {snapshot.current_step if snapshot else 'unknown'}",
        f"Next action: {snapshot.next_action if snapshot else 'unknown'}",
        f"Branch: {summary.branch or 'detached/unknown'}",
        f"Worktree: {summary.worktree_state}",
    ]
    if summary.changed_paths:
        lines.append("Changed paths:")
        lines.extend(f"- {path}" for path in summary.changed_paths)
    if summary.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in summary.warnings)
    if summary.errors:
        lines.append("Errors:")
        lines.extend(f"- {error}" for error in summary.errors)
    lines.append("Await learner confirmation before continuing.")
    return "\n".join(lines)
