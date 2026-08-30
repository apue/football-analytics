"""Offline command-line orchestration for academy conversion research."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .academy_analysis import run_academy_analysis
from .academy_baseline import verify_analysis_baseline
from .academy_conversion import resolve_roster_memberships
from .academy_conversion_io import (
    load_identity_resolutions,
    load_roster_candidates,
    write_resolved_rosters,
)
from .academy_conversion_report import render_report
from .academy_roster_parser import parse_reviewed_rosters
from .academy_sources import validate_source_evidence


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
    result = parse_reviewed_rosters(
        study_config_path=args.study_config,
        pdf_dir=args.pdf_dir,
        output_dir=args.output_dir,
    )
    _emit(result)
    return 0


def _analyze(args: argparse.Namespace) -> int:
    result = run_academy_analysis(
        study_config_path=args.study_config,
        rosters_path=args.rosters,
        appearances_path=args.appearances,
        competitions_path=args.competitions,
        coverage_path=args.coverage,
        output_dir=args.output_dir,
    )
    _emit({**result, "output_dir": str(args.output_dir)})
    return 0 if result["valid"] else 2


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


def _emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(dict(value), ensure_ascii=False, sort_keys=True))
