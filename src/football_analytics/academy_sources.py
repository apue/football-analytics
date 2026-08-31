"""Academy-specific approval of provider-independent evidence bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence_bundle import canonicalize_url, read_accepted_urls


def load_roster_source_config(path: Path) -> dict[str, Any]:
    """Load an approved, provider-independent roster source configuration."""

    try:
        config = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid source config {path}: {exc}") from exc
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("source config must be a schema-version-1 object")
    _only_fields(
        config,
        {
            "schema_version",
            "academy_id",
            "source_policy",
            "exit_cohort",
            "contracts",
            "pages",
        },
        "source config",
    )
    policy = config.get("source_policy")
    if not isinstance(policy, dict) or policy.get("status") != "approved":
        raise ValueError("source config must have approved source_policy")
    _only_fields(policy, {"status", "reviewed_at", "record"}, "source_policy")
    if not isinstance(policy.get("reviewed_at"), str) or not policy["reviewed_at"]:
        raise ValueError("approved source_policy requires reviewed_at")
    if not isinstance(policy.get("record"), str) or not policy["record"]:
        raise ValueError("approved source_policy requires a review record")
    pages = config.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("source config pages must be a non-empty list")
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("url"), str):
            raise ValueError("every source page must contain a URL")
        _only_fields(
            page,
            {
                "page_type",
                "filename",
                "season_start",
                "roster_page",
                "expected_player_count",
                "visual_review",
                "url",
            },
            "source page",
        )
        review = page.get("visual_review")
        if not isinstance(review, dict) or review.get("status") != "confirmed":
            raise ValueError("every source page requires confirmed visual_review")
        _only_fields(review, {"status", "reviewed_at"}, "visual_review")
        if not isinstance(review.get("reviewed_at"), str) or not review["reviewed_at"]:
            raise ValueError("confirmed visual_review requires reviewed_at")
    return config


def validate_source_evidence(
    source_config_path: Path, evidence_bundle_path: Path
) -> dict[str, Any]:
    """Check that every frozen academy source appears in accepted evidence."""

    config = load_roster_source_config(source_config_path)
    pages = config["pages"]

    required: set[str] = set()
    for page in pages:
        canonical = canonicalize_url(page["url"])
        if not canonical:
            raise ValueError(f"invalid source URL: {page['url']}")
        if canonical in required:
            raise ValueError(f"duplicate source URL: {canonical}")
        required.add(canonical)

    accepted = read_accepted_urls(evidence_bundle_path)
    missing = sorted(required - accepted)
    extra = sorted(accepted - required)
    return {
        "valid": not missing,
        "required": len(required),
        "found": len(required & accepted),
        "missing": missing,
        "accepted_extra": extra,
    }


def require_source_evidence(
    source_config_path: Path, evidence_bundle_path: Path
) -> dict[str, Any]:
    """Return the approved source config or fail on incomplete evidence."""

    result = validate_source_evidence(source_config_path, evidence_bundle_path)
    if not result["valid"]:
        raise ValueError(
            f"approved roster sources are missing from evidence: {result['missing']}"
        )
    return load_roster_source_config(source_config_path)


def _only_fields(value: dict[str, Any], fields: set[str], name: str) -> None:
    unsupported = sorted(set(value) - fields)
    if unsupported:
        raise ValueError(f"{name} has unsupported fields: {unsupported}")
