"""Command-line orchestration for academy conversion research runs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .academy_conversion import (
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
    manifest.add_argument("--config", type=Path, required=True)
    manifest.add_argument("--output", type=Path, required=True)

    acquire = commands.add_parser("acquire")
    acquire.add_argument("--config", type=Path, required=True)
    acquire.add_argument("--manifest", type=Path, required=True)
    acquire.add_argument("--run-dir", type=Path, required=True)
    acquire.add_argument("--env-file", type=Path)
    acquire.add_argument("--shard-index", type=int, default=0)
    acquire.add_argument("--shard-count", type=int, default=1)

    validate = commands.add_parser("validate-run")
    validate.add_argument("--run-dir", type=Path, required=True)

    analyze = commands.add_parser("analyze")
    analyze.add_argument("--rosters", type=Path, required=True)
    analyze.add_argument("--appearances", type=Path, required=True)
    analyze.add_argument("--competitions", type=Path, required=True)
    analyze.add_argument("--coverage", type=Path, required=True)
    analyze.add_argument("--output-dir", type=Path, required=True)
    analyze.add_argument("--exit-start", type=int, required=True)
    analyze.add_argument("--exit-end", type=int, required=True)
    analyze.add_argument("--thresholds", default="10,15,20")

    resolve = commands.add_parser("resolve-rosters")
    resolve.add_argument("--candidates", type=Path, required=True)
    resolve.add_argument("--resolutions", type=Path, required=True)
    resolve.add_argument("--output", type=Path, required=True)
    resolve.add_argument("--validation", type=Path, required=True)

    parse_rosters = commands.add_parser("parse-official-rosters")
    parse_rosters.add_argument("--config", type=Path, required=True)
    parse_rosters.add_argument("--run-dir", type=Path, required=True)
    parse_rosters.add_argument("--output-dir", type=Path, required=True)

    prototype = commands.add_parser("build-match-row-prototype")
    prototype.add_argument("--rosters", type=Path, required=True)
    prototype.add_argument("--links", type=Path, required=True)
    prototype.add_argument("--games", type=Path, required=True)
    prototype.add_argument("--appearances", type=Path, required=True)
    prototype.add_argument("--competition-policy", type=Path, required=True)
    prototype.add_argument("--output-dir", type=Path, required=True)
    prototype.add_argument("--source-url", required=True)

    merge_links = commands.add_parser("merge-source-link-proposals")
    merge_links.add_argument("--base", type=Path, required=True)
    merge_links.add_argument("--proposal", type=Path, action="append", required=True)
    merge_links.add_argument("--source-players", type=Path, required=True)
    merge_links.add_argument("--output", type=Path, required=True)

    report = commands.add_parser("render-report")
    report.add_argument("--summary", type=Path, required=True)
    report.add_argument("--outcomes", type=Path, required=True)
    report.add_argument("--rosters", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--primary-threshold", type=int, default=15)
    report.add_argument("--appearances", type=Path)
    report.add_argument("--competition-policy", type=Path)
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
    try:
        config = load_keypool_config(args.env_file)
        payload = FirecrawlClient(config).scrape(args.url)
        document = validate_firecrawl_document(
            payload,
            ContentContract(tuple(args.required_text), args.min_profile_links),
        )
    except Exception as exc:
        _emit(
            {
                "service": "keypool-firecrawl",
                "target_contract": "failed",
                "error_type": type(exc).__name__,
                "error": _safe_error(exc),
            }
        )
        return 2
    _emit(
        {
            "service": "keypool-firecrawl",
            "target_contract": "passed",
            "target_status": document.target_status,
            "content_format": document.content_format,
            "content_sha256": document.content_sha256,
        }
    )
    return 0


def _manifest(args: argparse.Namespace) -> int:
    config = _load_object(args.config)
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
    config = _load_object(args.config)
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
    records_dir = args.run_dir / "records"
    records = (
        [_load_object(path) for path in sorted(records_dir.glob("*.json"))]
        if records_dir.exists()
        else []
    )
    counts = Counter(str(record.get("status", "invalid")) for record in records)
    ready = bool(records) and set(counts) == {"complete"}
    payload = {
        "run_dir": str(args.run_dir),
        "record_count": len(records),
        "counts": dict(sorted(counts.items())),
        "ready_for_parse": ready,
    }
    validation_path = args.run_dir / "validation.json"
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.write_text(json.dumps(payload, indent=2) + "\n")
    _emit(payload)
    return 0 if ready else 2


def _analyze(args: argparse.Namespace) -> int:
    thresholds = tuple(int(value) for value in args.thresholds.split(","))
    if not thresholds or any(value < 1 for value in thresholds):
        raise SystemExit("thresholds must be positive integers")
    memberships = load_roster_memberships(args.rosters)
    appearances = load_appearances(args.appearances)
    rules = load_competition_rules(args.competitions)
    coverage = load_coverage(args.coverage)
    issues = validate_research_rows(memberships, appearances, rules, coverage)
    cohorts = build_exit_cohorts(
        memberships, exit_start=args.exit_start, exit_end=args.exit_end
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

    config = _load_object(args.config)
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
    policy_version, competition_policy = load_competition_policy(
        args.competition_policy
    )
    facts = build_match_row_prototype_facts(
        load_roster_memberships(args.rosters),
        load_source_player_links(args.links),
        args.games,
        args.appearances,
        competition_policy,
        source_url=args.source_url,
        scope_id=policy_version,
    )
    write_prototype_facts(args.output_dir, facts)
    payload = {
        "appearance_rows": len(facts.appearances),
        "competition_rules": len(facts.rules),
        "coverage_rows": len(facts.coverage),
        "scope_id": policy_version,
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
    render_report(
        args.summary,
        args.outcomes,
        args.rosters,
        args.output,
        primary_threshold=args.primary_threshold,
        appearances_path=args.appearances,
        competition_policy_path=args.competition_policy,
    )
    _emit({"report": str(args.output)})
    return 0


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def _safe_error(exc: Exception) -> str:
    return str(exc) if isinstance(exc, AcquisitionError) else type(exc).__name__


def _emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
