"""Course state, lesson handoff, and read-only resume inspection."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

STATE_RELATIVE_PATH = Path("course/state.yaml")
REQUIRED_STATE_KEYS = {
    "schema_version",
    "current_stage",
    "current_lesson",
    "completed_lessons",
    "updated_at",
}
RETIRED_STATE_KEYS = {"status", "next_action", "open_questions", "last_updated"}
ALLOWED_LESSON_STATUSES = {
    "ready",
    "in_progress",
    "paused",
    "review",
    "completed",
    "blocked",
}
REQUIRED_HANDOFF_FIELDS = {
    "lesson_id",
    "stage",
    "status",
    "checkpoint_id",
    "current_step",
    "next_action",
    "updated_at",
}
REQUIRED_HANDOFF_SECTIONS = {
    "Completed",
    "Current Work",
    "Decisions",
    "Validation",
    "Open Questions",
    "Checkpoint History",
}
REQUIRED_TEMPLATES = {
    "analysis.ipynb",
    "brief.md",
    "checks.md",
    "exercises.md",
    "findings.md",
    "handoff.md",
}
CHECKPOINT_ID_PATTERN = re.compile(r"^CP-\d{3}$")
CHECKPOINT_SUBJECT_PATTERN = re.compile(
    r"^checkpoint\((?P<lesson>[^)]+)\): "
    r"(?P<checkpoint>CP-\d{3}) (?P<step>.+)$"
)
HISTORY_ENTRY_PATTERN = re.compile(
    r"^- (?P<checkpoint>CP-\d{3}) \| "
    r"(?P<updated_at>[^|]+?) \| "
    r"(?P<status>[^|]+?) \| "
    r"(?P<step>.+)$"
)


@dataclass(frozen=True)
class CheckpointHistoryEntry:
    """One concise checkpoint record from a handoff."""

    checkpoint_id: str
    updated_at: str
    status: str
    step: str


@dataclass(frozen=True)
class Handoff:
    """Parsed handoff metadata and checkpoint history."""

    metadata: dict[str, Any]
    sections: frozenset[str]
    history: tuple[CheckpointHistoryEntry, ...]


@dataclass(frozen=True)
class ResumeSummary:
    """Read-only recovery information for one repository."""

    lesson_id: str | None
    stage: int | None
    status: str | None
    checkpoint_id: str | None
    current_step: str | None
    next_action: str | None
    updated_at: str | None
    branch: str | None
    worktree_state: str
    changed_paths: tuple[str, ...]
    checkpoint_commit_exists: bool
    checkpoint_commit: str | None
    latest_checkpoint_id: str | None
    checkpoint_matches_latest: bool
    errors: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        """Whether state, handoff, and checkpoint history agree."""

        return not self.errors


def _load_yaml_mapping(path: Path, label: str) -> tuple[dict[str, Any], list[str]]:
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
    except ValueError:
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
    return True


def parse_handoff(path: Path) -> tuple[Handoff | None, list[str]]:
    """Parse a handoff with YAML frontmatter and required Markdown sections."""

    try:
        text = path.read_text()
    except OSError as error:
        return None, [f"Could not read handoff {path}: {error}"]

    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if match is None:
        return None, [f"Handoff missing YAML frontmatter: {path}"]

    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        return None, [f"Invalid handoff frontmatter in {path}: {error}"]
    if not isinstance(metadata, dict):
        return None, [f"Handoff frontmatter must be a mapping: {path}"]

    body = text[match.end() :]
    sections = frozenset(
        section.strip() for section in re.findall(r"^## (.+?)\s*$", body, re.MULTILINE)
    )
    history_match = re.search(
        r"^## Checkpoint History\s*$\r?\n(?P<body>.*?)(?=^## |\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )
    history: list[CheckpointHistoryEntry] = []
    errors: list[str] = []
    if history_match is not None:
        for line in history_match.group("body").splitlines():
            stripped_line = line.strip()
            entry_match = HISTORY_ENTRY_PATTERN.match(stripped_line)
            if entry_match is not None:
                history.append(
                    CheckpointHistoryEntry(
                        checkpoint_id=entry_match.group("checkpoint"),
                        updated_at=entry_match.group("updated_at").strip(),
                        status=entry_match.group("status").strip(),
                        step=entry_match.group("step").strip(),
                    )
                )
            elif stripped_line.startswith("- "):
                errors.append(
                    "Invalid checkpoint history entry; expected "
                    "'- CP-NNN | updated_at | status | step': "
                    f"{stripped_line}"
                )

    return Handoff(metadata, sections, tuple(history)), errors


def _validate_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_STATE_KEYS - state.keys()
    if missing:
        errors.append(f"Course state missing keys: {sorted(missing)}")
    retired = RETIRED_STATE_KEYS & state.keys()
    if retired:
        errors.append(f"Course state contains retired keys: {sorted(retired)}")
    unexpected = state.keys() - REQUIRED_STATE_KEYS - RETIRED_STATE_KEYS
    if unexpected:
        errors.append(f"Course state contains unexpected keys: {sorted(unexpected)}")
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
    elif len(completed) != len(set(completed)):
        errors.append("Course state completed_lessons must not contain duplicates")
    if not _is_timestamp(state.get("updated_at")):
        errors.append("Course state updated_at must be an ISO date or timestamp")
    return errors


def _validate_handoff(
    handoff: Handoff,
    *,
    expected_lesson_id: str,
    expected_stage: object,
) -> list[str]:
    errors: list[str] = []
    metadata = handoff.metadata
    missing = REQUIRED_HANDOFF_FIELDS - metadata.keys()
    if missing:
        errors.append(f"Handoff frontmatter missing keys: {sorted(missing)}")
    unexpected = metadata.keys() - REQUIRED_HANDOFF_FIELDS
    if unexpected:
        errors.append(f"Handoff frontmatter has unexpected keys: {sorted(unexpected)}")
    if metadata.get("lesson_id") != expected_lesson_id:
        errors.append(
            "Handoff lesson_id does not match global current_lesson: "
            f"{metadata.get('lesson_id')!r} != {expected_lesson_id!r}"
        )
    if metadata.get("stage") != expected_stage:
        errors.append(
            "Handoff stage does not match global current_stage: "
            f"{metadata.get('stage')!r} != {expected_stage!r}"
        )
    status = metadata.get("status")
    if status not in ALLOWED_LESSON_STATUSES:
        errors.append(f"Invalid handoff status: {status!r}")
    checkpoint_id = metadata.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not CHECKPOINT_ID_PATTERN.fullmatch(
        checkpoint_id
    ):
        errors.append("Handoff checkpoint_id must match CP-NNN")
    for field in ("current_step", "next_action"):
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Handoff {field} must be non-empty")
    if not _is_timestamp(metadata.get("updated_at")):
        errors.append("Handoff updated_at must be an ISO date or timestamp")

    missing_sections = REQUIRED_HANDOFF_SECTIONS - handoff.sections
    if missing_sections:
        errors.append(f"Handoff missing sections: {sorted(missing_sections)}")
    if not handoff.history:
        errors.append("Handoff Checkpoint History has no valid entries")
    else:
        checkpoint_numbers = [
            int(entry.checkpoint_id.removeprefix("CP-")) for entry in handoff.history
        ]
        if checkpoint_numbers != sorted(set(checkpoint_numbers)):
            errors.append("Handoff checkpoint history must be unique and increasing")
        for entry in handoff.history:
            if entry.status not in ALLOWED_LESSON_STATUSES:
                errors.append(f"Invalid checkpoint history status: {entry.status!r}")
            if not _is_timestamp(entry.updated_at):
                errors.append(
                    "Checkpoint history updated_at must be an ISO date or timestamp"
                )
            if not entry.step:
                errors.append("Checkpoint history step must be non-empty")
        latest = handoff.history[-1]
        if latest.checkpoint_id != checkpoint_id:
            errors.append(
                "Handoff latest checkpoint history entry does not match "
                f"frontmatter checkpoint_id: {latest.checkpoint_id!r} "
                f"!= {checkpoint_id!r}"
            )
        if latest.status != status:
            errors.append(
                "Handoff latest checkpoint history status does not match "
                f"frontmatter status: {latest.status!r} != {status!r}"
            )
    return errors


def validate_course(root: Path) -> list[str]:
    """Validate state v2, the active lesson handoff, and lesson templates."""

    root = root.resolve()
    state_path = root / STATE_RELATIVE_PATH
    if not state_path.is_file():
        return [f"Missing course state: {STATE_RELATIVE_PATH}"]

    state, errors = _load_yaml_mapping(state_path, "course state")
    errors.extend(_validate_state(state))

    lesson_id = state.get("current_lesson")
    if isinstance(lesson_id, str) and lesson_id:
        lesson_dir = root / "course" / "lessons" / lesson_id
        if not lesson_dir.is_dir():
            errors.append(f"Current lesson directory does not exist: {lesson_id}")
        else:
            brief_path = lesson_dir / "brief.md"
            handoff_path = lesson_dir / "handoff.md"
            if not brief_path.is_file():
                errors.append(f"Current lesson missing brief.md: {lesson_id}")
            if not handoff_path.is_file():
                errors.append(f"Current lesson missing handoff.md: {lesson_id}")
            else:
                handoff, handoff_errors = parse_handoff(handoff_path)
                errors.extend(handoff_errors)
                if handoff is not None:
                    errors.extend(
                        _validate_handoff(
                            handoff,
                            expected_lesson_id=lesson_id,
                            expected_stage=state.get("current_stage"),
                        )
                    )
                    completed_lessons = state.get("completed_lessons")
                    if isinstance(completed_lessons, list):
                        is_completed = handoff.metadata.get("status") == "completed"
                        is_listed = lesson_id in completed_lessons
                        if is_completed and not is_listed:
                            errors.append(
                                "Completed current lesson must appear in "
                                "course state completed_lessons"
                            )
                        elif not is_completed and is_listed:
                            errors.append(
                                "Current lesson appears in completed_lessons but "
                                "handoff status is not completed"
                            )

    template_dir = root / "course" / "templates"
    if not template_dir.is_dir():
        errors.append("Missing course templates directory")
    else:
        actual_templates = {
            path.name for path in template_dir.iterdir() if path.is_file()
        }
        missing_templates = REQUIRED_TEMPLATES - actual_templates
        if missing_templates:
            errors.append(f"Missing course templates: {sorted(missing_templates)}")
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
        message = result.stderr.strip() or result.stdout.strip()
        return "", f"Git command failed ({' '.join(args)}): {message}"
    return result.stdout, None


def _git_checkpoint_commits(
    root: Path, lesson_id: str
) -> tuple[list[tuple[str, str]], str | None]:
    output, error = _run_git(root, "log", "--all", "--format=%H%x00%s")
    if error is not None:
        return [], error
    commits: list[tuple[str, str]] = []
    for line in output.splitlines():
        commit_hash, separator, subject = line.partition("\0")
        if not separator:
            continue
        match = CHECKPOINT_SUBJECT_PATTERN.fullmatch(subject)
        if match is not None and match.group("lesson") == lesson_id:
            commits.append((commit_hash, match.group("checkpoint")))
    return commits, None


def build_resume_summary(root: Path) -> ResumeSummary:
    """Inspect the current course and Git repository without modifying either."""

    root = root.resolve()
    errors = validate_course(root)
    state, state_errors = _load_yaml_mapping(root / STATE_RELATIVE_PATH, "course state")
    for error in state_errors:
        if error not in errors:
            errors.append(error)

    lesson_id_value = state.get("current_lesson")
    lesson_id = lesson_id_value if isinstance(lesson_id_value, str) else None
    handoff: Handoff | None = None
    if lesson_id:
        handoff_path = root / "course" / "lessons" / lesson_id / "handoff.md"
        if handoff_path.is_file():
            handoff, _ = parse_handoff(handoff_path)
    metadata = handoff.metadata if handoff is not None else {}

    branch_output, branch_error = _run_git(root, "branch", "--show-current")
    if branch_error is not None:
        errors.append(branch_error)
    branch = branch_output.strip() or None

    status_output, status_error = _run_git(root, "status", "--porcelain")
    if status_error is not None:
        errors.append(status_error)
    changed_paths = tuple(
        line[3:] for line in status_output.splitlines() if len(line) >= 4
    )
    worktree_state = "dirty" if changed_paths else "clean"

    checkpoint_id_value = metadata.get("checkpoint_id")
    checkpoint_id = (
        checkpoint_id_value if isinstance(checkpoint_id_value, str) else None
    )
    checkpoint_commit: str | None = None
    latest_checkpoint_id: str | None = None
    checkpoint_commit_exists = False
    checkpoint_matches_latest = False
    if lesson_id and checkpoint_id:
        commits, commit_error = _git_checkpoint_commits(root, lesson_id)
        if commit_error is not None:
            errors.append(commit_error)
        elif commits:
            latest_checkpoint_id = commits[0][1]
            matching = [
                commit_hash for commit_hash, cp_id in commits if cp_id == checkpoint_id
            ]
            checkpoint_commit_exists = bool(matching)
            checkpoint_commit = matching[0] if matching else None
            checkpoint_matches_latest = (
                checkpoint_commit_exists and latest_checkpoint_id == checkpoint_id
            )
            if not checkpoint_matches_latest:
                errors.append(
                    f"Handoff checkpoint is {checkpoint_id}, but latest Git "
                    f"checkpoint is {latest_checkpoint_id}"
                )
        else:
            errors.append(
                f"Local checkpoint commit not found for {lesson_id} {checkpoint_id}"
            )

    stage_value = metadata.get("stage")
    stage = stage_value if isinstance(stage_value, int) else None
    return ResumeSummary(
        lesson_id=lesson_id,
        stage=stage,
        status=_optional_string(metadata.get("status")),
        checkpoint_id=checkpoint_id,
        current_step=_optional_string(metadata.get("current_step")),
        next_action=_optional_string(metadata.get("next_action")),
        updated_at=_optional_string(metadata.get("updated_at")),
        branch=branch,
        worktree_state=worktree_state,
        changed_paths=changed_paths,
        checkpoint_commit_exists=checkpoint_commit_exists,
        checkpoint_commit=checkpoint_commit,
        latest_checkpoint_id=latest_checkpoint_id,
        checkpoint_matches_latest=checkpoint_matches_latest,
        errors=tuple(dict.fromkeys(errors)),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def render_resume_summary(summary: ResumeSummary) -> str:
    """Render a concise learner-facing recovery summary."""

    checkpoint_commit = (
        summary.checkpoint_commit[:12] if summary.checkpoint_commit else "unknown"
    )
    lines = [
        "Course resume summary",
        f"Lesson: {summary.lesson_id or 'unknown'}",
        f"Stage: {summary.stage if summary.stage is not None else 'unknown'}",
        f"Status: {summary.status or 'unknown'}",
        f"Checkpoint: {summary.checkpoint_id or 'unknown'}",
        f"Current step: {summary.current_step or 'unknown'}",
        f"Next action: {summary.next_action or 'unknown'}",
        f"Updated at: {summary.updated_at or 'unknown'}",
        f"Branch: {summary.branch or 'detached/unknown'}",
        (
            "Checkpoint commit exists: "
            f"{'yes' if summary.checkpoint_commit_exists else 'no'}"
        ),
        f"Checkpoint commit: {checkpoint_commit}",
        f"Latest Git checkpoint: {summary.latest_checkpoint_id or 'unknown'}",
        (
            "Checkpoint matches latest: "
            f"{'yes' if summary.checkpoint_matches_latest else 'no'}"
        ),
        f"Worktree: {summary.worktree_state}",
    ]
    if summary.worktree_state == "dirty":
        lines.append("Recovery note: post-checkpoint uncommitted work requires review.")
        lines.append("Changed paths:")
        lines.extend(f"- {path}" for path in summary.changed_paths)
    if summary.errors:
        lines.append("Problems:")
        lines.extend(f"- {error}" for error in summary.errors)
    lines.append("Await learner confirmation before continuing.")
    return "\n".join(lines)
