"""Offline command-line orchestration for academy conversion research."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .academy_baseline import verify_analysis_baseline
from .academy_conversion import (
    RosterMembership,
    build_exit_cohorts,
    calculate_player_outcomes,
    resolve_roster_memberships,
    summarize_outcomes,
    validate_research_rows,
)
from .academy_conversion_io import (
    load_appearances,
    load_competition_rules,
    load_coverage,
    load_identity_resolutions,
    load_roster_candidates,
    load_roster_memberships,
    write_analysis_artifacts,
    write_resolved_rosters,
    write_roster_candidates,
)
from .academy_conversion_report import render_report
from .academy_roster_parser import parse_roster_blocks
from .academy_sources import load_roster_source_config, validate_source_evidence
from .academy_study import AcademyStudyConfig, load_academy_study_config


def main(argv: Sequence[str] | None = None) -> int:
    """Run one offline academy research stage."""

    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-sources":
            return _validate_sources(args)
        if args.command == "resolve-rosters":
            return _resolve_rosters(args)
        if args.command == "parse-official-rosters":
            return _parse_official_rosters(args)
        if args.command == "analyze":
            return _analyze(args)
        if args.command == "verify-baseline":
            return _verify_baseline(args)
        return _render_report(args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="academy-conversion")
    commands = parser.add_subparsers(dest="command", required=True)

    sources = commands.add_parser("validate-sources")
    sources.add_argument("--source-config", type=Path, required=True)
    sources.add_argument("--evidence", type=Path, required=True)

    resolve = commands.add_parser("resolve-rosters")
    resolve.add_argument("--candidates", type=Path, required=True)
    resolve.add_argument("--resolutions", type=Path, required=True)
    resolve.add_argument("--output", type=Path, required=True)
    resolve.add_argument("--validation", type=Path, required=True)

    parse_rosters = commands.add_parser("parse-official-rosters")
    parse_rosters.add_argument("--study-config", type=Path, required=True)
    parse_rosters.add_argument("--source-config", type=Path, required=True)
    parse_rosters.add_argument("--pdf-dir", type=Path, required=True)
    parse_rosters.add_argument("--output-dir", type=Path, required=True)

    analyze = commands.add_parser("analyze")
    analyze.add_argument("--study-config", type=Path, required=True)
    analyze.add_argument("--rosters", type=Path, required=True)
    analyze.add_argument("--appearances", type=Path, required=True)
    analyze.add_argument("--competitions", type=Path, required=True)
    analyze.add_argument("--coverage", type=Path, required=True)
    analyze.add_argument("--output-dir", type=Path, required=True)

    baseline = commands.add_parser("verify-baseline")
    baseline.add_argument("--analysis-dir", type=Path, required=True)
    baseline.add_argument("--coverage", type=Path, required=True)
    baseline.add_argument("--baseline", type=Path, required=True)

    report = commands.add_parser("render-report")
    report.add_argument("--study-config", type=Path, required=True)
    report.add_argument("--summary", type=Path, required=True)
    report.add_argument("--outcomes", type=Path, required=True)
    report.add_argument("--appearances", type=Path, required=True)
    report.add_argument("--competitions", type=Path, required=True)
    return parser


def _validate_sources(args: argparse.Namespace) -> int:
    result = validate_source_evidence(args.source_config, args.evidence)
    _emit(result)
    return 0 if result["valid"] else 2


def _resolve_rosters(args: argparse.Namespace) -> int:
    candidates = load_roster_candidates(args.candidates)
    resolutions = load_identity_resolutions(args.resolutions)
    memberships, issues = resolve_roster_memberships(candidates, resolutions)
    write_resolved_rosters(args.output, args.validation, memberships, issues)
    _emit(
        {
            "confirmed": len(memberships),
            "issues": len(issues),
            "valid": not issues,
        }
    )
    return 0 if not issues else 2


def _parse_official_rosters(args: argparse.Namespace) -> int:
    try:
        import pymupdf
    except ImportError as exc:
        raise ValueError(
            "pymupdf is required; run with: uv run --with pymupdf "
            "academy-conversion parse-official-rosters ..."
        ) from exc

    study = load_academy_study_config(args.study_config, require_approved=True)
    if args.source_config.resolve() != Path(study.roster_source_config_path).resolve():
        raise ValueError("source config does not match the frozen study")
    _require_within(args.output_dir, Path(study.run_dir), "output directory")
    config = load_roster_source_config(args.source_config)
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
        pdf_path = args.pdf_dir / filename
        _require_within(pdf_path, args.pdf_dir, "roster PDF")
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
    write_roster_candidates(args.output_dir / "roster_candidates.csv", all_candidates)
    validation = {
        "valid": True,
        "season_count": len(checks),
        "candidate_count": len(all_candidates),
        "checks": checks,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n"
    )
    _emit(validation)
    return 0


def _analyze(args: argparse.Namespace) -> int:
    study = load_academy_study_config(args.study_config, require_approved=True)
    _require_within(args.output_dir, Path(study.run_dir), "output directory")
    memberships = load_roster_memberships(args.rosters)
    _validate_memberships_for_study(memberships, study)
    appearances = load_appearances(args.appearances)
    rules = load_competition_rules(args.competitions)
    coverage = load_coverage(args.coverage)

    actual_scope_ids = {row.scope_id for row in coverage}
    if actual_scope_ids != {study.adult_source_scope_id}:
        raise ValueError(
            "coverage facts do not match study adult-source scope: "
            f"expected={study.adult_source_scope_id}, actual={sorted(actual_scope_ids)}"
        )
    policy = _load_object(Path(study.competition_policy_path))
    policy_version = str(policy.get("policy_version", ""))
    actual_policy_versions = {row.policy_version for row in rules}
    if actual_policy_versions != {policy_version}:
        raise ValueError(
            "competition facts do not match study policy: "
            f"expected={policy_version}, actual={sorted(actual_policy_versions)}"
        )

    issues = validate_research_rows(memberships, appearances, rules, coverage)
    cohorts = build_exit_cohorts(
        memberships,
        exit_start=study.exit_season_start,
        exit_end=study.exit_season_end,
    )
    outcomes = []
    summary = []
    if not issues:
        outcomes = calculate_player_outcomes(
            cohorts,
            appearances,
            rules,
            coverage,
            thresholds=study.sensitivity_thresholds,
            observation_season_count=study.observation_season_count,
            sustained_qualifying_seasons=study.sustained_qualifying_seasons,
        )
        summary = summarize_outcomes(outcomes, thresholds=study.sensitivity_thresholds)
    write_analysis_artifacts(
        args.output_dir,
        cohorts,
        outcomes,
        summary,
        issues,
        thresholds=study.sensitivity_thresholds,
        provenance={
            "input_artifacts": {
                "rosters": str(args.rosters),
                "appearances": str(args.appearances),
                "competitions": str(args.competitions),
                "coverage": str(args.coverage),
            },
            "roster_source_urls": sorted({row.source_url for row in memberships}),
            "appearance_source_urls": sorted({row.source_url for row in appearances}),
            "coverage_source_urls": sorted({row.source_url for row in coverage}),
            "policy_versions": sorted(actual_policy_versions),
            "adult_source_scope_id": study.adult_source_scope_id,
            "study_config": str(args.study_config),
            "study": study.summary(),
        },
    )
    _emit(
        {
            "valid": not issues,
            "issue_count": len(issues),
            "player_count": len(cohorts),
            "output_dir": str(args.output_dir),
        }
    )
    return 0 if not issues else 2


def _render_report(args: argparse.Namespace) -> int:
    output = render_report(
        args.summary,
        args.outcomes,
        args.appearances,
        args.competitions,
        args.study_config,
    )
    _emit({"report": str(output)})
    return 0


def _verify_baseline(args: argparse.Namespace) -> int:
    result = verify_analysis_baseline(args.analysis_dir, args.coverage, args.baseline)
    _emit(result)
    return 0 if result["valid"] else 2


def _validate_memberships_for_study(
    memberships: Sequence[RosterMembership], study: AcademyStudyConfig
) -> None:
    academies = {row.academy_id for row in memberships}
    if academies != {study.academy_id}:
        raise ValueError(
            "roster facts do not match study academy: "
            f"expected={study.academy_id}, actual={sorted(academies)}"
        )
    expected_seasons = set(
        range(study.roster_season_start, study.roster_season_end + 1)
    )
    actual_seasons = {row.season_start for row in memberships}
    if actual_seasons != expected_seasons:
        raise ValueError(
            "roster facts do not cover configured seasons: "
            f"expected={sorted(expected_seasons)}, actual={sorted(actual_seasons)}"
        )

    source_config = load_roster_source_config(Path(study.roster_source_config_path))
    if source_config.get("academy_id") != study.academy_id:
        raise ValueError("roster source academy does not match study")
    pages = source_config.get("pages")
    if not isinstance(pages, list):
        raise ValueError("roster source pages must be a list")
    expected_counts: Counter[int] = Counter()
    for page in pages:
        if not isinstance(page, Mapping):
            raise ValueError("roster source page must be an object")
        try:
            season = int(page["season_start"])
            count = int(page["expected_player_count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "roster source pages require season_start and expected_player_count"
            ) from exc
        if count < 1:
            raise ValueError("expected_player_count must be positive")
        expected_counts[season] += count
    actual_counts = Counter(row.season_start for row in memberships)
    if actual_counts != expected_counts:
        raise ValueError(
            "roster fact counts do not match source contract: "
            f"expected={dict(expected_counts)}, actual={dict(actual_counts)}"
        )


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _require_within(path: Path, parent: Path, label: str) -> None:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must be inside configured run directory") from exc


def _emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), ensure_ascii=False, sort_keys=True))
