"""Deterministic parsing of visually confirmed academy roster PDF blocks."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from pathlib import Path

from .academy_conversion import RosterCandidate
from .academy_conversion_io import write_roster_candidates
from .academy_sources import require_source_evidence
from .academy_study import load_academy_study_config

PdfBlock = tuple[float, float, float, float, str]

_ROLE_PATTERN = re.compile(
    r"^(PORTERO|PORTERS?|PORTER|DEFENSA|DEFENSES?|"
    r"CENTROCAMPISTA|MIGCAMPISTA|DELANTERO|DAVANTER):\s*(.+)$",
    re.IGNORECASE,
)
_ROLE_SECTION_PATTERN = re.compile(
    r"(PORTERO|PORTERS?|PORTER|DEFENSA|DEFENSES?|"
    r"CENTROCAMPISTA|MIGCAMPISTA|DELANTERO|DAVANTER):\s*(.*?)"
    r"(?=(?:PORTERO|PORTERS?|PORTER|DEFENSA|DEFENSES?|CENTROCAMPISTA|"
    r"MIGCAMPISTA|DELANTERO|DAVANTER|ENTRENADOR|SEGUNDO ENTRENADOR):|$)",
    re.IGNORECASE,
)
_POSITIONS = {
    "portero": "goalkeeper",
    "porter": "goalkeeper",
    "porters": "goalkeeper",
    "defensa": "defender",
    "defense": "defender",
    "defenses": "defender",
    "centrocampista": "midfielder",
    "migcampista": "midfielder",
    "delantero": "forward",
    "davanter": "forward",
}


def parse_reviewed_rosters(
    *,
    study_config_path: Path,
    pdf_dir: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Parse every reviewed PDF declared by one approved academy study."""

    try:
        import pymupdf
    except ImportError as exc:
        raise ValueError(
            "pymupdf is required; run with: uv run --with pymupdf "
            "academy-conversion parse-official-rosters ..."
        ) from exc

    study = load_academy_study_config(study_config_path)
    _require_within(output_dir, Path(study.run_dir), "output directory")
    config = require_source_evidence(
        Path(study.roster_source_config_path), Path(study.roster_evidence_path)
    )
    if config.get("academy_id") != study.academy_id:
        raise ValueError("roster source academy does not match study")
    pages = config["pages"]
    expected_seasons = set(
        range(study.roster_season_start, study.roster_season_end + 1)
    )
    actual_seasons = {int(page.get("season_start", -1)) for page in pages}
    if actual_seasons != expected_seasons:
        raise ValueError("roster source seasons do not match the frozen study")

    all_candidates = []
    checks = []
    for page_config in pages:
        filename = page_config.get("filename")
        if not isinstance(filename, str) or not filename:
            raise ValueError("every roster source page requires filename")
        pdf_path = pdf_dir / filename
        _require_within(pdf_path, pdf_dir, "roster PDF")
        source_page = int(page_config["roster_page"])
        with pymupdf.open(pdf_path) as document:
            if not 1 <= source_page <= len(document):
                raise ValueError(f"roster page out of range: {filename}")
            pdf_page = document[source_page - 1]
            blocks = [(*block[:4], block[4]) for block in pdf_page.get_text("blocks")]
        candidates = parse_roster_blocks(
            blocks,
            academy_id=study.academy_id,
            season_start=int(page_config["season_start"]),
            source_url=str(page_config["url"]),
            source_page=source_page,
        )
        expected_count = int(page_config["expected_player_count"])
        if len(candidates) != expected_count:
            raise ValueError(
                "roster count mismatch: "
                f"season={page_config['season_start']} "
                f"actual={len(candidates)} expected={expected_count}"
            )
        all_candidates.extend(candidates)
        with pdf_path.open("rb") as handle:
            content_sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
        checks.append(
            {
                "season_start": int(page_config["season_start"]),
                "source_page": source_page,
                "player_count": len(candidates),
                "content_sha256": content_sha256,
            }
        )
    write_roster_candidates(output_dir / "roster_candidates.csv", all_candidates)
    validation: dict[str, object] = {
        "valid": True,
        "season_count": len(checks),
        "candidate_count": len(all_candidates),
        "checks": checks,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n"
    )
    return validation


def parse_roster_blocks(
    blocks: Iterable[PdfBlock],
    *,
    academy_id: str,
    season_start: int,
    source_url: str,
    source_page: int,
) -> list[RosterCandidate]:
    """Parse player rows inside one visually verified Juvenil A page region."""

    block_rows = list(blocks)
    headings = [row for row in block_rows if _normalized_heading(row[4]) == "JUVENIL A"]
    if len(headings) != 1:
        raise ValueError(f"expected one JUVENIL A heading, found {len(headings)}")
    heading_y = headings[0][1]
    later_squad_headings = [
        row[1]
        for row in block_rows
        if row[1] > heading_y
        and _normalized_heading(row[4]).startswith("JUVENIL ")
        and _normalized_heading(row[4]) != "JUVENIL A"
    ]
    region_end = min(later_squad_headings) if later_squad_headings else float("inf")

    candidates: list[RosterCandidate] = []
    region_blocks = [block for block in block_rows if heading_y < block[1] < region_end]
    for block in sorted(region_blocks, key=lambda row: (row[1], row[0])):
        text = _block_text_with_continuations(block, region_blocks)
        sections = [
            (_POSITIONS[match.group(1).casefold()], match.group(2))
            for match in _ROLE_SECTION_PATTERN.finditer(text)
        ]
        if not sections:
            position = _POSITIONS.get(text.rstrip(":").casefold())
            names_text = _paired_value(block, region_blocks) if position else ""
            sections = [(position, names_text)] if position and names_text else []
        for position, names_text in sections:
            for displayed_name in _split_names(names_text):
                ordinal = len(candidates)
                candidate_id = hashlib.sha256(
                    (
                        f"{academy_id}\0{season_start}\0{source_url}\0{source_page}"
                        f"\0{position}\0{displayed_name}\0{ordinal}"
                    ).encode()
                ).hexdigest()[:20]
                candidates.append(
                    RosterCandidate(
                        candidate_id,
                        displayed_name,
                        academy_id,
                        season_start,
                        source_url,
                        source_page,
                        position,
                    )
                )
    if not candidates:
        raise ValueError("no roster player rows found")
    return candidates


def _normalized_heading(text: str) -> str:
    return " ".join(text.upper().split())


def _split_names(value: str) -> list[str]:
    names = []
    for comma_part in value.split(","):
        names.extend(re.split(r"\s+(?:y|i)\s+", comma_part, flags=re.IGNORECASE))
    return [name.strip() for name in names if name.strip()]


def _paired_value(label: PdfBlock, blocks: Iterable[PdfBlock]) -> str:
    candidates = [
        block
        for block in blocks
        if block[0] > label[2] and abs(block[1] - label[1]) < 2
    ]
    if not candidates:
        return ""
    return " ".join(min(candidates, key=lambda row: row[0])[4].split())


def _block_text_with_continuations(block: PdfBlock, blocks: Iterable[PdfBlock]) -> str:
    parts = [" ".join(block[4].split())]
    if not _ROLE_SECTION_PATTERN.search(parts[0]):
        return parts[0]
    current = block
    remaining = list(blocks)
    while True:
        followers = [
            candidate
            for candidate in remaining
            if candidate != current
            and abs(candidate[0] - block[0]) < 10
            and 0 <= candidate[1] - current[3] <= 4
        ]
        if not followers:
            break
        follower = min(followers, key=lambda row: row[1])
        follower_text = " ".join(follower[4].split())
        if (
            _ROLE_SECTION_PATTERN.search(follower_text)
            or "ENTRENADOR:" in follower_text.upper()
        ):
            break
        parts.append(follower_text)
        current = follower
    return " ".join(parts)


def _require_within(path: Path, parent: Path, label: str) -> None:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must be inside configured run directory") from exc
