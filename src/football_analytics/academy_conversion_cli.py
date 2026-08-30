"""Command-line orchestration for academy conversion research runs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

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
from .academy_conversion_prototype import (
    build_match_row_prototype_facts,
    load_competition_policy,
    load_source_player_ids,
    load_source_player_links,
    merge_source_link_proposals,
    write_prototype_facts,
    write_source_player_links,
)
from .academy_conversion_report import render_report
from .academy_roster_parser import parse_roster_blocks
from .academy_study import AcademyStudyConfig, load_academy_study_config
from .web_acquisition import (
    AcquisitionError,
    ContentContract,
    FileContract,
    FirecrawlClient,
    acquire_firecrawl_item,
    acquire_http_file_item,
    build_manifest,
    download_http_file,
    load_keypool_config,
    validate_firecrawl_document,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="academy-conversion")
    commands = parser.add_subparsers(dest="command", required=True)

    health = commands.add_parser("health")
    health.add_argument("--env-file", type=Path, required=True)
    health.add_argument("--url", required=True)
    health.add_argument("--required-text", action="append", default=[])
    health.add_argument("--min-profile-links", type=int, default=0)

    manifest = commands.add_parser("manifest")
    manifest.add_argument("--study-config", type=Path, required=True)
    manifest.add_argument("--config", type=Path, required=True)
    manifest.add_argument("--output", type=Path, required=True)

    acquire = commands.add_parser("acquire")
    acquire.add_argument("--study-config", type=Path, required=True)
    acquire.add_argument("--config", type=Path, required=True)
    acquire.add_argument("--manifest", type=Path, required=True)
    acquire.add_argument("--run-dir", type=Path, required=True)
    acquire.add_argument("--env-file", type=Path)
    acquire.add_argument("--shard-index", type=int, default=0)
    acquire.add_argument("--shard-count", type=int, default=1)

    validate = commands.add_parser("validate-run")
    validate.add_argument("--study-config", type=Path, required=True)
    validate.add_argument("--run-dir", type=Path, required=True)

    analyze = commands.add_parser("analyze")
    analyze.add_argument("--rosters", type=Path, required=True)
    analyze.add_argument("--appearances", type=Path, required=True)
    analyze.add_argument("--competitions", type=Path, required=True)
    analyze.add_argument("--coverage", type=Path, required=True)
    analyze.add_argument("--output-dir", type=Path, required=True)
    analyze.add_argument("--study-config", type=Path, required=True)

    resolve = commands.add_parser("resolve-rosters")
    resolve.add_argument("--candidates", type=Path, required=True)
    resolve.add_argument("--resolutions", type=Path, required=True)
    resolve.add_argument("--output", type=Path, required=True)
    resolve.add_argument("--validation", type=Path, required=True)

    parse_rosters = commands.add_parser("parse-official-rosters")
    parse_rosters.add_argument("--study-config", type=Path, required=True)
    parse_rosters.add_argument("--config", type=Path, required=True)
    parse_rosters.add_argument("--run-dir", type=Path, required=True)
    parse_rosters.add_argument("--output-dir", type=Path, required=True)

    prototype = commands.add_parser("build-match-row-prototype")
    prototype.add_argument("--rosters", type=Path, required=True)
    prototype.add_argument("--links", type=Path, required=True)
    prototype.add_argument("--games", type=Path, required=True)
    prototype.add_argument("--appearances", type=Path, required=True)
    prototype.add_argument("--output-dir", type=Path, required=True)
    prototype.add_argument("--study-config", type=Path, required=True)

    merge_links = commands.add_parser("merge-source-link-proposals")
    merge_links.add_argument("--base", type=Path, required=True)
    merge_links.add_argument("--proposal", type=Path, action="append", required=True)
    merge_links.add_argument("--source-players", type=Path, required=True)
    merge_links.add_argument("--output", type=Path, required=True)

    report = commands.add_parser("render-report")
    report.add_argument("--summary", type=Path, required=True)
    report.add_argument("--outcomes", type=Path, required=True)
    report.add_argument("--appearances", type=Path, required=True)
    report.add_argument("--competitions", type=Path, required=True)
    report.add_argument("--study-config", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "health":
        return _health(args)
    if args.command == "manifest":
        return _manifest(args)
    if args.command == "acquire":
        return _acquire(args)
    if args.command == "validate-run":
        return _validate_run(args)
    if args.command == "analyze":
        return _analyze(args)
    if args.command == "resolve-rosters":
        return _resolve_rosters(args)
    if args.command == "parse-official-rosters":
        return _parse_official_rosters(args)
    if args.command == "build-match-row-prototype":
        return _build_match_row_prototype(args)
    if args.command == "merge-source-link-proposals":
        return _merge_source_link_proposals(args)
    return _render_report(args)


def _health(args: argparse.Namespace) -> int:
    checks = {
        "keypool": "not_checked",
        "transport": "not_checked",
        "firecrawl": "not_checked",
        "target_page": "not_checked",
        "content": "not_checked",
        "parser": "not_checked",
    }

    def fail(gate: str, exc: Exception) -> int:
        checks[gate] = "failed"
        _emit(
            {
                "service": "keypool-firecrawl",
                "checks": checks,
                "error_type": type(exc).__name__,
                "error": _safe_error(exc),
            }
        )
        return 2

    try:
        config = load_keypool_config(args.env_file)
    except Exception as exc:
        return fail("keypool", exc)
    checks["keypool"] = "passed"

    try:
        payload = FirecrawlClient(config).scrape(args.url)
    except Exception as exc:
        return fail("transport", exc)
    checks["transport"] = "passed"

    data = payload.get("data")
    if payload.get("success") is not True or not isinstance(data, Mapping):
        return fail("firecrawl", AcquisitionError("firecrawl response failed"))
    checks["firecrawl"] = "passed"

    metadata = data.get("metadata")
    target_status = (
        metadata.get("statusCode") if isinstance(metadata, Mapping) else None
    )
    if not isinstance(target_status, int) or not 200 <= target_status < 300:
        return fail("target_page", AcquisitionError(f"target_status={target_status}"))
    checks["target_page"] = "passed"

    try:
        document = validate_firecrawl_document(
            payload,
            ContentContract(tuple(args.required_text), args.min_profile_links),
        )
    except Exception as exc:
        return fail("content", exc)
    checks["content"] = "passed"

    try:
        parser_probe = parse_roster_blocks(
            [
                (0.0, 0.0, 50.0, 10.0, "JUVENIL A"),
                (0.0, 20.0, 80.0, 30.0, "PORTERO: Parser Probe"),
            ],
            academy_id="health-probe",
            season_start=2000,
            source_url="health://parser-probe",
            source_page=1,
        )
        if not parser_probe:
            raise ValueError("parser probe returned no rows")
    except Exception as exc:
        return fail("parser", exc)
    checks["parser"] = "passed"

    _emit(
        {
            "service": "keypool-firecrawl",
            "checks": checks,
            "target_status": document.target_status,
            "content_format": document.content_format,
            "content_sha256": document.content_sha256,
        }
    )
    return 0


def _manifest(args: argparse.Namespace) -> int:
    study = _validate_study_paths(args, require_output_within_run=True)
    config = _load_object(args.config)
    _validate_roster_source_config(config, study)
    pages = config.get("pages")
    if not isinstance(pages, list):
        raise SystemExit("config pages must be a list")
    rows = build_manifest(pages, provider=str(config.get("provider", "firecrawl")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    )
    _emit({"manifest": str(args.output), "item_count": len(rows)})
    return 0


def _acquire(args: argparse.Namespace) -> int:
    study = _validate_study_paths(args)
    config = _load_object(args.config)
    _validate_roster_source_config(config, study)
    policy = config.get("source_policy")
    if not isinstance(policy, Mapping) or policy.get("status") != "approved":
        raise SystemExit("source policy is not approved")
    if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
        raise SystemExit("invalid shard index/count")

    provider = str(config.get("provider", "firecrawl"))
    if provider == "firecrawl":
        if args.env_file is None:
            raise SystemExit("--env-file is required for firecrawl")
        client = FirecrawlClient(load_keypool_config(args.env_file))
    elif provider == "http-file":
        client = None
    else:
        raise SystemExit(f"unsupported provider: {provider}")
    contracts = config.get("contracts")
    if not isinstance(contracts, Mapping):
        contracts = {}
    rows = [json.loads(line) for line in args.manifest.read_text().splitlines() if line]
    expected_rows = build_manifest(config["pages"], provider=provider)
    if rows != expected_rows:
        raise SystemExit("manifest does not match the frozen roster source config")
    selected = [
        row
        for index, row in enumerate(rows)
        if index % args.shard_count == args.shard_index
    ]
    counts: Counter[str] = Counter()
    for row in selected:
        contract_value = contracts.get(str(row.get("page_type", "default")), {})
        if not isinstance(contract_value, Mapping):
            contract_value = {}
        if provider == "firecrawl":
            contract = ContentContract(
                required_text=tuple(contract_value.get("required_text", ())),
                min_profile_links=int(contract_value.get("min_profile_links", 0)),
            )
            result = acquire_firecrawl_item(client, row, args.run_dir, contract)
        else:
            magic_prefix = str(contract_value.get("magic_prefix", "")).encode()
            if contract_value.get("magic_prefix_hex"):
                magic_prefix = bytes.fromhex(str(contract_value["magic_prefix_hex"]))
            file_contract = FileContract(
                content_types=tuple(contract_value.get("content_types", ())),
                magic_prefix=magic_prefix,
                tail_marker=str(contract_value.get("tail_marker", "")).encode(),
                min_bytes=int(contract_value.get("min_bytes", 1)),
            )
            result = acquire_http_file_item(
                download_http_file, row, args.run_dir, file_contract
            )
        counts[result.status] += 1
    _emit(
        {
            "shard_index": args.shard_index,
            "shard_count": args.shard_count,
            "assigned": len(selected),
            "counts": dict(sorted(counts.items())),
        }
    )
    return 0 if set(counts) <= {"complete"} else 2


def _validate_run(args: argparse.Namespace) -> int:
    study = _validate_study_paths(args)
    config = _load_object(Path(study.roster_source_config_path))
    _validate_roster_source_config(config, study)
    manifest_path = args.run_dir / "manifest.jsonl"
    manifest_rows = [
        json.loads(line) for line in manifest_path.read_text().splitlines() if line
    ]
    expected_manifest = build_manifest(
        config["pages"], provider=str(config.get("provider", "firecrawl"))
    )
    manifest_matches = manifest_rows == expected_manifest
    records_dir = args.run_dir / "records"
    records = (
        [_load_object(path) for path in sorted(records_dir.glob("*.json"))]
        if records_dir.exists()
        else []
    )
    counts = Counter(str(record.get("status", "invalid")) for record in records)
    expected_ids = {str(row["item_id"]) for row in expected_manifest}
    record_ids = {str(record.get("item_id", "")) for record in records}
    records_match = record_ids == expected_ids and len(records) == len(expected_ids)
    ready = (
        bool(records)
        and manifest_matches
        and records_match
        and set(counts) == {"complete"}
    )
    payload = {
        "run_dir": str(args.run_dir),
        "record_count": len(records),
        "counts": dict(sorted(counts.items())),
        "manifest_matches_study": manifest_matches,
        "records_match_manifest": records_match,
        "ready_for_parse": ready,
    }
    validation_path = args.run_dir / "validation.json"
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.write_text(json.dumps(payload, indent=2) + "\n")
    _emit(payload)
    return 0 if ready else 2


def _analyze(args: argparse.Namespace) -> int:
    study = _validate_study_paths(args, require_output_within_run=True)
    thresholds = study.sensitivity_thresholds
    memberships = load_roster_memberships(args.rosters)
    _validate_memberships_for_study(memberships, study)
    appearances = load_appearances(args.appearances)
    rules = load_competition_rules(args.competitions)
    coverage = load_coverage(args.coverage)
    actual_scope_ids = {row.scope_id for row in coverage}
    if actual_scope_ids != {study.adult_source_scope_id}:
        raise SystemExit(
            "coverage facts do not match study adult-source scope: "
            f"expected={study.adult_source_scope_id}, actual={sorted(actual_scope_ids)}"
        )
    study_policy_version, _ = load_competition_policy(
        Path(study.competition_policy_path)
    )
    actual_policy_versions = {row.policy_version for row in rules}
    if actual_policy_versions != {study_policy_version}:
        raise SystemExit(
            "competition facts do not match study policy: "
            f"expected={study_policy_version}, actual={sorted(actual_policy_versions)}"
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
            thresholds=thresholds,
            observation_season_count=study.observation_season_count,
            sustained_qualifying_seasons=study.sustained_qualifying_seasons,
        )
        summary = summarize_outcomes(outcomes, thresholds=thresholds)
    write_analysis_artifacts(
        args.output_dir,
        cohorts,
        outcomes,
        summary,
        issues,
        thresholds=thresholds,
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
            "policy_versions": sorted({row.policy_version for row in rules}),
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


def _resolve_rosters(args: argparse.Namespace) -> int:
    candidates = load_roster_candidates(args.candidates)
    resolutions = load_identity_resolutions(args.resolutions)
    memberships, issues = resolve_roster_memberships(candidates, resolutions)
    write_resolved_rosters(args.output, args.validation, memberships, issues)
    payload = {
        "confirmed": len(memberships),
        "issues": len(issues),
        "valid": not issues,
    }
    _emit(payload)
    return 0 if not issues else 2


def _parse_official_rosters(args: argparse.Namespace) -> int:
    try:
        import pymupdf
    except ImportError as exc:
        raise SystemExit(
            "pymupdf is required; run with: uv run --with pymupdf "
            "academy-conversion parse-official-rosters ..."
        ) from exc

    study = _validate_study_paths(args, require_output_within_run=True)
    config = _load_object(args.config)
    _validate_roster_source_config(config, study)
    pages = config.get("pages")
    if not isinstance(pages, list):
        raise SystemExit("config pages must be a list")
    records_dir = args.run_dir / "records"
    records = {
        str(record["url"]): record
        for path in records_dir.glob("*.json")
        if (record := _load_object(path)).get("status") == "complete"
    }
    all_candidates = []
    checks = []
    evidence_dir = args.output_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for page_config in pages:
        if not isinstance(page_config, Mapping):
            raise SystemExit("page config must be an object")
        url = str(page_config.get("url", ""))
        review = page_config.get("visual_review")
        if not isinstance(review, Mapping) or review.get("status") != "confirmed":
            raise SystemExit(f"visual review is not confirmed: {url}")
        record = records.get(url)
        if record is None:
            raise SystemExit(f"complete acquisition record not found: {url}")
        source_page = int(page_config["roster_page"])
        raw_path = args.run_dir / str(record["raw_path"])
        document = pymupdf.open(raw_path)
        if not 1 <= source_page <= len(document):
            raise SystemExit(f"roster page out of range: {url}")
        pdf_page = document[source_page - 1]
        blocks = [(*block[:4], block[4]) for block in pdf_page.get_text("blocks")]
        candidates = parse_roster_blocks(
            blocks,
            academy_id=str(config["academy_id"]),
            season_start=int(page_config["season_start"]),
            source_url=url,
            source_page=source_page,
        )
        expected = int(page_config["expected_player_count"])
        if len(candidates) != expected:
            raise SystemExit(
                f"roster count mismatch: season={page_config['season_start']} "
                f"actual={len(candidates)} expected={expected}"
            )
        pdf_page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False).save(
            evidence_dir / f"{page_config['season_start']}.png"
        )
        all_candidates.extend(candidates)
        checks.append(
            {
                "season_start": int(page_config["season_start"]),
                "source_page": source_page,
                "player_count": len(candidates),
                "content_sha256": record.get("content_sha256"),
                "visual_review": dict(review),
            }
        )
    output_path = args.output_dir / "roster_candidates.csv"
    write_roster_candidates(output_path, all_candidates)
    validation = {
        "valid": True,
        "season_count": len(checks),
        "candidate_count": len(all_candidates),
        "checks": checks,
    }
    (args.output_dir / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n"
    )
    _emit(validation)
    return 0


def _build_match_row_prototype(args: argparse.Namespace) -> int:
    study = _validate_study_paths(args, require_output_within_run=True)
    policy_version, competition_policy = load_competition_policy(
        Path(study.competition_policy_path)
    )
    memberships = load_roster_memberships(args.rosters)
    _validate_memberships_for_study(memberships, study)
    facts = build_match_row_prototype_facts(
        memberships,
        load_source_player_links(args.links),
        args.games,
        args.appearances,
        competition_policy,
        source_url=study.adult_source_public_url,
        policy_version=policy_version,
        coverage_scope_id=study.adult_source_scope_id,
        exit_start=study.exit_season_start,
        exit_end=study.exit_season_end,
        observation_season_count=study.observation_season_count,
    )
    write_prototype_facts(args.output_dir, facts)
    payload = {
        "appearance_rows": len(facts.appearances),
        "competition_rules": len(facts.rules),
        "coverage_rows": len(facts.coverage),
        "policy_version": policy_version,
        "coverage_scope_id": study.adult_source_scope_id,
    }
    _emit(payload)
    return 0


def _merge_source_link_proposals(args: argparse.Namespace) -> int:
    base = load_source_player_links(args.base)
    proposals = [
        row
        for proposal_path in args.proposal
        for row in load_source_player_links(proposal_path)
    ]
    merged = merge_source_link_proposals(
        base,
        proposals,
        valid_source_ids=load_source_player_ids(args.source_players),
    )
    write_source_player_links(args.output, merged)
    confirmed = sum(row.status == "confirmed" for row in merged)
    _emit(
        {
            "link_rows": len(merged),
            "confirmed": confirmed,
            "unresolved": len(merged) - confirmed,
            "output": str(args.output),
        }
    )
    return 0


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


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def _validate_study_paths(
    args: argparse.Namespace, *, require_output_within_run: bool = False
) -> AcademyStudyConfig:
    """Prevent acquisition stages from drifting from their frozen study."""

    study = load_academy_study_config(args.study_config, require_approved=True)
    expected_config = Path(study.roster_source_config_path).resolve()
    if hasattr(args, "config") and args.config.resolve() != expected_config:
        raise SystemExit(
            "roster source config does not match study config: "
            f"expected={expected_config}, actual={args.config.resolve()}"
        )
    expected_run_dir = Path(study.run_dir).resolve()
    if hasattr(args, "run_dir") and args.run_dir.resolve() != expected_run_dir:
        raise SystemExit(
            "run directory does not match study config: "
            f"expected={expected_run_dir}, actual={args.run_dir.resolve()}"
        )
    if hasattr(args, "manifest"):
        expected_manifest = expected_run_dir / "manifest.jsonl"
        if args.manifest.resolve() != expected_manifest:
            raise SystemExit(
                "manifest path does not match configured run directory: "
                f"expected={expected_manifest}, actual={args.manifest.resolve()}"
            )
    if require_output_within_run and hasattr(args, "output"):
        expected_manifest = expected_run_dir / "manifest.jsonl"
        if args.output.resolve() != expected_manifest:
            raise SystemExit(
                "manifest output does not match configured run directory: "
                f"expected={expected_manifest}, actual={args.output.resolve()}"
            )
    if require_output_within_run and hasattr(args, "output_dir"):
        _require_path_within(args.output_dir, expected_run_dir, "output directory")
    return study


def _require_path_within(path: Path, parent: Path, label: str) -> None:
    try:
        path.resolve().relative_to(parent)
    except ValueError as exc:
        raise SystemExit(f"{label} must be inside configured run directory") from exc


def _validate_roster_source_config(
    config: Mapping[str, Any], study: AcademyStudyConfig
) -> None:
    academy_id = str(config.get("academy_id", ""))
    if academy_id != study.academy_id:
        raise SystemExit(
            "roster source academy does not match study config: "
            f"expected={study.academy_id}, actual={academy_id}"
        )
    source_policy = config.get("source_policy")
    source_status = (
        str(source_policy.get("status", ""))
        if isinstance(source_policy, Mapping)
        else ""
    )
    if source_status != study.roster_source_policy_status:
        raise SystemExit(
            "roster source policy does not match study config: "
            f"expected={study.roster_source_policy_status}, actual={source_status}"
        )
    pages = config.get("pages")
    if not isinstance(pages, list):
        raise SystemExit("config pages must be a list")
    try:
        seasons = {int(page["season_start"]) for page in pages}
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(
            "every roster source page needs an integer season_start"
        ) from exc
    expected = set(range(study.roster_season_start, study.roster_season_end + 1))
    if seasons != expected:
        raise SystemExit(
            "roster source seasons do not match study config: "
            f"expected={sorted(expected)}, actual={sorted(seasons)}"
        )


def _validate_memberships_for_study(
    memberships: Sequence[RosterMembership], study: AcademyStudyConfig
) -> None:
    unexpected_academies = sorted(
        {row.academy_id for row in memberships if row.academy_id != study.academy_id}
    )
    if unexpected_academies:
        raise SystemExit(
            "roster facts do not match study academy: "
            f"expected={study.academy_id}, actual={unexpected_academies}"
        )
    out_of_window = sorted(
        {
            row.season_start
            for row in memberships
            if not study.roster_season_start
            <= row.season_start
            <= study.roster_season_end
        }
    )
    if out_of_window:
        raise SystemExit(
            "roster facts fall outside configured roster seasons: "
            f"actual={out_of_window}"
        )
    expected_seasons = set(
        range(study.roster_season_start, study.roster_season_end + 1)
    )
    actual_seasons = {row.season_start for row in memberships}
    missing_seasons = sorted(expected_seasons - actual_seasons)
    if missing_seasons:
        raise SystemExit(
            f"roster facts do not cover configured seasons: missing={missing_seasons}"
        )


def _safe_error(exc: Exception) -> str:
    return str(exc) if isinstance(exc, AcquisitionError) else type(exc).__name__


def _emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
