"""Pinned local access to the Soccer Analytics ML companion repository."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import tomllib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BookReferenceError(RuntimeError):
    """Raised when the pinned book reference cannot be used safely."""


@dataclass(frozen=True)
class BookReferenceSpec:
    """Versioned source contract for one teaching reference repository."""

    key: str
    name: str
    url: str
    commit: str
    checkout: str


SOURCE_KEY = "soccer_analytics_ml"
SEARCH_SUFFIXES = {".ipynb", ".md", ".py", ".rst", ".txt"}


def load_reference_spec(
    manifest_path: Path,
    source_key: str = SOURCE_KEY,
) -> BookReferenceSpec:
    """Load and validate a reference source from the committed TOML manifest."""
    try:
        payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise BookReferenceError(f"Cannot read reference manifest: {error}") from error

    if payload.get("schema_version") != 1:
        raise BookReferenceError("Reference manifest schema_version must be 1.")

    sources = payload.get("source")
    if not isinstance(sources, dict):
        raise BookReferenceError("Reference manifest must contain a source table.")
    source = sources.get(source_key)
    if not isinstance(source, dict):
        raise BookReferenceError(f"Reference source is missing: {source_key}")

    required = ("name", "url", "commit", "checkout")
    missing = [field for field in required if not source.get(field)]
    if missing:
        raise BookReferenceError(
            f"Reference source {source_key} is missing: {', '.join(missing)}"
        )

    commit = str(source["commit"])
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise BookReferenceError("Reference commit must be a full 40-character SHA.")

    return BookReferenceSpec(
        key=source_key,
        name=str(source["name"]),
        url=str(source["url"]),
        commit=commit,
        checkout=str(source["checkout"]),
    )


def _git(repository: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise BookReferenceError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def _normalized_remote(value: str) -> str:
    return value.rstrip("/").removesuffix(".git")


def reference_status(
    repository: Path,
    spec: BookReferenceSpec,
) -> dict[str, Any]:
    """Report whether the local clone is clean and at the manifest commit."""
    repository = repository.resolve()
    base = {
        "checkout": spec.checkout,
        "name": spec.name,
        "path": str(repository),
        "source_url": spec.url,
        "expected_commit": spec.commit,
    }
    if not repository.exists():
        return {**base, "state": "missing", "ready": False}
    if not (repository / ".git").is_dir():
        return {**base, "state": "not_git", "ready": False}

    current_commit = _git(repository, "rev-parse", "HEAD")
    dirty = bool(_git(repository, "status", "--porcelain"))
    remote_url = _git(repository, "remote", "get-url", "origin", check=False)
    source_matches = _normalized_remote(remote_url) == _normalized_remote(spec.url)
    pinned = current_commit == spec.commit
    ready = pinned and not dirty and source_matches
    if dirty:
        state = "dirty"
    elif not source_matches:
        state = "source_mismatch"
    elif not pinned:
        state = "commit_mismatch"
    else:
        state = "ready"
    return {
        **base,
        "state": state,
        "ready": ready,
        "current_commit": current_commit,
        "dirty": dirty,
        "remote_url": remote_url or None,
        "source_matches": source_matches,
    }


def _ensure_clean_repository(repository: Path) -> None:
    if _git(repository, "status", "--porcelain"):
        raise BookReferenceError(
            f"Reference repository has local changes: {repository}. "
            "Preserve or remove them before syncing."
        )


def sync_reference(
    repository: Path,
    spec: BookReferenceSpec,
) -> dict[str, Any]:
    """Materialize the exact manifest commit without following an upstream branch."""
    repository = repository.resolve()
    if repository.exists():
        if not (repository / ".git").is_dir():
            raise BookReferenceError(
                f"Refusing to replace non-Git reference path: {repository}"
            )
        _ensure_clean_repository(repository)
        remote_url = _git(repository, "remote", "get-url", "origin", check=False)
        if _normalized_remote(remote_url) != _normalized_remote(spec.url):
            raise BookReferenceError(
                f"Reference origin does not match manifest: {remote_url or '<missing>'}"
            )
        if _git(repository, "rev-parse", "HEAD") != spec.commit:
            has_commit = (
                subprocess.run(
                    ["git", "-C", str(repository), "cat-file", "-e", spec.commit],
                    check=False,
                    capture_output=True,
                ).returncode
                == 0
            )
            if not has_commit:
                _git(repository, "fetch", "--depth", "1", "origin", spec.commit)
            _git(repository, "checkout", "--detach", spec.commit)
        return reference_status(repository, spec)

    repository.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=repository.parent,
        prefix=".book-reference-clone.",
    ) as temporary_root:
        clone = Path(temporary_root) / "repository"
        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth=1",
                "--filter=blob:none",
                "--no-checkout",
                spec.url,
                str(clone),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise BookReferenceError(f"Reference clone failed: {detail}")
        has_commit = (
            subprocess.run(
                ["git", "-C", str(clone), "cat-file", "-e", spec.commit],
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )
        if not has_commit:
            _git(clone, "fetch", "--depth", "1", "origin", spec.commit)
        _git(clone, "checkout", "--detach", spec.commit)
        os.replace(clone, repository)

    status = reference_status(repository, spec)
    if not status["ready"]:
        raise BookReferenceError(
            f"Reference checkout did not reach pinned commit: {spec.commit}"
        )
    return status


def require_ready(repository: Path, spec: BookReferenceSpec) -> None:
    """Reject queries against missing, modified, or unpinned source material."""
    status = reference_status(repository, spec)
    if status["ready"]:
        return
    raise BookReferenceError(
        f"Book reference is not ready ({status['state']}). "
        "Run `uv run book-ref sync` explicitly."
    )


def _chapter_matches(path: Path, chapter: str | None) -> bool:
    if chapter is None:
        return True
    normalized = chapter.strip().casefold().replace("chapter", "").strip(" -_")
    path_text = path.as_posix().casefold()
    return any(
        token in path_text
        for token in (f"chapter-{normalized}", f"chapter_{normalized}")
    )


def _matcher(query: str, regex: bool) -> re.Pattern[str]:
    if not query:
        raise BookReferenceError("Search query cannot be empty.")
    try:
        expression = query if regex else re.escape(query)
        return re.compile(expression, re.IGNORECASE)
    except re.error as error:
        raise BookReferenceError(f"Invalid search expression: {error}") from error


def _source_text(source: str | list[str]) -> str:
    return source if isinstance(source, str) else "".join(source)


def _notebook_matches(
    path: Path,
    relative_path: str,
    pattern: re.Pattern[str],
    cell_type: str | None,
) -> Iterable[dict[str, Any]]:
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BookReferenceError(
            f"Cannot parse notebook {relative_path}: {error}"
        ) from error

    for cell_index, cell in enumerate(notebook.get("cells", [])):
        current_type = cell.get("cell_type")
        if cell_type and current_type != cell_type:
            continue
        for line_number, line in enumerate(
            _source_text(cell.get("source", "")).splitlines(),
            start=1,
        ):
            if pattern.search(line):
                yield {
                    "path": relative_path,
                    "cell": cell_index,
                    "cell_type": current_type,
                    "line": line_number,
                    "snippet": line.strip(),
                }


def _text_matches(
    path: Path,
    relative_path: str,
    pattern: re.Pattern[str],
) -> Iterable[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    for line_number, line in enumerate(lines, start=1):
        if pattern.search(line):
            yield {
                "path": relative_path,
                "line": line_number,
                "kind": "text",
                "snippet": line.strip(),
            }


def _searchable_paths(repository: Path) -> Iterator[Path]:
    for directory, children, filenames in os.walk(repository):
        children[:] = sorted(child for child in children if child != ".git")
        root = Path(directory)
        for filename in sorted(filenames):
            yield root / filename


def search_reference(
    repository: Path,
    spec: BookReferenceSpec,
    query: str,
    *,
    chapter: str | None = None,
    cell_type: str | None = None,
    regex: bool = False,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search notebook sources and text files without indexing stored outputs."""
    if limit < 1:
        raise BookReferenceError("Search limit must be at least 1.")
    require_ready(repository, spec)
    pattern = _matcher(query, regex)
    matches: list[dict[str, Any]] = []
    for path in _searchable_paths(repository):
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix.casefold() not in SEARCH_SUFFIXES:
            continue
        relative = path.relative_to(repository)
        if not _chapter_matches(relative, chapter):
            continue
        if path.suffix.casefold() == ".ipynb":
            candidates = _notebook_matches(
                path,
                relative.as_posix(),
                pattern,
                cell_type,
            )
        elif cell_type is None:
            candidates = _text_matches(path, relative.as_posix(), pattern)
        else:
            continue
        for match in candidates:
            matches.append(match)
            if len(matches) == limit:
                return matches
    return matches


def _safe_reference_path(repository: Path, relative_path: str) -> Path:
    if Path(relative_path).is_absolute():
        raise BookReferenceError("Reference path must be relative to the repository.")
    repository = repository.resolve()
    candidate = (repository / relative_path).resolve()
    if not candidate.is_relative_to(repository):
        raise BookReferenceError("Reference path escapes the repository.")
    if not candidate.is_file():
        raise BookReferenceError(f"Reference file does not exist: {relative_path}")
    return candidate


def show_reference(
    repository: Path,
    spec: BookReferenceSpec,
    relative_path: str,
    *,
    cell: int | None = None,
) -> dict[str, Any]:
    """Return a text file or one notebook cell with stable location metadata."""
    require_ready(repository, spec)
    path = _safe_reference_path(repository, relative_path)
    if path.suffix.casefold() != ".ipynb":
        if cell is not None:
            raise BookReferenceError("--cell can only be used with a notebook.")
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise BookReferenceError(
                f"Cannot read reference file {relative_path}: {error}"
            ) from error
        return {"path": relative_path, "kind": "text", "content": content}

    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BookReferenceError(
            f"Cannot parse notebook {relative_path}: {error}"
        ) from error
    cells = notebook.get("cells", [])
    if cell is None:
        return {
            "path": relative_path,
            "kind": "notebook_index",
            "cells": [
                {
                    "cell": index,
                    "cell_type": item.get("cell_type"),
                    "first_line": next(
                        iter(_source_text(item.get("source", "")).splitlines()),
                        "",
                    ),
                }
                for index, item in enumerate(cells)
            ],
        }
    if cell < 0 or cell >= len(cells):
        raise BookReferenceError(
            f"Notebook cell {cell} is outside 0..{max(len(cells) - 1, 0)}."
        )
    selected = cells[cell]
    return {
        "path": relative_path,
        "kind": "notebook_cell",
        "cell": cell,
        "cell_type": selected.get("cell_type"),
        "content": _source_text(selected.get("source", "")),
    }
