import json

import pytest

from football_analytics.academy_sources import validate_source_evidence


def _write_source_config(path, urls, **extra):
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "academy_id": "academy",
                "source_policy": {
                    "status": "approved",
                    "reviewed_at": "2026-08-31",
                    "record": "docs/sources/academy.md",
                },
                "pages": [
                    {
                        "url": url,
                        "visual_review": {
                            "status": "confirmed",
                            "reviewed_at": "2026-08-31",
                        },
                    }
                    for url in urls
                ],
                **extra,
            }
        )
    )


def _write_bundle(path, urls):
    path.write_text(
        "".join(
            json.dumps(
                {
                    "schema_version": 1,
                    "decision": "accepted",
                    "canonical_url": url,
                }
            )
            + "\n"
            for url in urls
        )
    )


def test_source_validation_requires_all_frozen_urls_and_reports_extra(tmp_path):
    source_config = tmp_path / "sources.json"
    bundle = tmp_path / "evidence.jsonl"
    _write_source_config(
        source_config,
        ["https://official.test/2015.pdf", "https://official.test/2016.pdf"],
    )
    _write_bundle(
        bundle,
        ["https://official.test/2015.pdf", "https://official.test/extra.pdf"],
    )

    result = validate_source_evidence(source_config, bundle)

    assert result == {
        "valid": False,
        "required": 2,
        "found": 1,
        "missing": ["https://official.test/2016.pdf"],
        "accepted_extra": ["https://official.test/extra.pdf"],
    }


def test_source_validation_accepts_a_complete_frozen_bundle(tmp_path):
    source_config = tmp_path / "sources.json"
    bundle = tmp_path / "evidence.jsonl"
    urls = ["https://official.test/2015.pdf", "https://official.test/2016.pdf"]
    _write_source_config(source_config, urls)
    _write_bundle(bundle, urls)

    result = validate_source_evidence(source_config, bundle)

    assert result["valid"] is True
    assert result["found"] == 2
    assert result["missing"] == []


def test_source_validation_rejects_deprecated_provider_switch(tmp_path):
    source_config = tmp_path / "sources.json"
    bundle = tmp_path / "evidence.jsonl"
    _write_source_config(
        source_config,
        ["https://official.test/2015.pdf"],
        provider="http-file",
    )
    _write_bundle(bundle, ["https://official.test/2015.pdf"])

    with pytest.raises(ValueError, match="provider is obsolete"):
        validate_source_evidence(source_config, bundle)
