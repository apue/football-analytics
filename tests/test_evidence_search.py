import json
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest

from football_analytics.evidence_bundle import canonicalize_url, read_accepted_urls
from football_analytics.evidence_search import (
    EvidenceSearchError,
    FirecrawlSearchClient,
    KeyPoolConfig,
    load_keypool_config,
    load_search_config,
    replay_evidence_search,
    run_evidence_search,
)


def _write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "queries": [
                    {"id": "season-2015", "query": "Barcelona 2015 PDF"},
                    {"id": "season-2016", "query": "Barcelona 2016 PDF"},
                ],
                "limit": 20,
                "country": "ES",
                "allowed_domains": ["fcbarcelona.com", "example.test"],
                "require_pdf": True,
                "required_url_terms": ["report"],
            }
        )
    )


def test_keypool_config_is_normalized_and_redacted(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("KEYPOOL_URL=keypool.example.test/\nKEYPOOL_KEY=secret\n")
    monkeypatch.setenv("KEYPOOL_URL", "ignored.example.test")

    config = load_keypool_config(env_file)

    assert config == KeyPoolConfig("https://keypool.example.test", "secret")
    assert "secret" not in repr(config)


def test_keypool_config_can_come_from_environment(monkeypatch):
    monkeypatch.setenv("KEYPOOL_URL", "https://keypool.example.test/")
    monkeypatch.setenv("KEYPOOL_KEY", "secret")

    assert load_keypool_config() == KeyPoolConfig(
        "https://keypool.example.test", "secret"
    )


def test_keypool_config_rejects_missing_values(monkeypatch):
    monkeypatch.delenv("KEYPOOL_URL", raising=False)
    monkeypatch.delenv("KEYPOOL_KEY", raising=False)

    with pytest.raises(EvidenceSearchError, match="KEYPOOL_URL"):
        load_keypool_config()


def test_firecrawl_client_uses_keypool_search_contract():
    calls = []

    def request(method, url, headers, payload):
        calls.append((method, url, headers, payload))
        return {"success": True, "data": {"web": []}}

    client = FirecrawlSearchClient(
        KeyPoolConfig("https://keypool.example.test", "secret"),
        request_json=request,
    )
    client.search(
        "Barcelona annual report",
        limit=12,
        country="ES",
        require_pdf=True,
    )

    method, url, headers, payload = calls[0]
    assert method == "POST"
    assert url == "https://keypool.example.test/v2/search"
    assert headers["Authorization"] == "Bearer secret"
    assert headers["x-keypool-service"] == "firecrawl"
    assert payload == {
        "query": "Barcelona annual report",
        "limit": 12,
        "country": "ES",
        "sources": [{"type": "web"}],
        "categories": [{"type": "pdf"}],
    }


def test_firecrawl_client_does_not_request_pdf_category_when_not_required():
    calls = []

    def request(method, url, headers, payload):
        calls.append(payload)
        return {"success": True, "data": {"web": []}}

    client = FirecrawlSearchClient(
        KeyPoolConfig("https://keypool.example.test", "secret"),
        request_json=request,
    )
    client.search("official roster", limit=10, country="NL", require_pdf=False)

    assert "categories" not in calls[0]


def test_firecrawl_http_error_surfaces_safe_provider_message(monkeypatch):
    def fail(request, timeout):
        raise HTTPError(
            request.full_url,
            403,
            "Forbidden",
            {},
            BytesIO(b'{"success":false,"error":"account disabled"}'),
        )

    monkeypatch.setattr("football_analytics.evidence_search.urlopen", fail)
    client = FirecrawlSearchClient(
        KeyPoolConfig("https://keypool.example.test", "secret")
    )

    with pytest.raises(
        EvidenceSearchError, match="HTTP 403: account disabled"
    ) as captured:
        client.search("query", limit=10, country="ES", require_pdf=True)
    assert "secret" not in str(captured.value)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "HTTPS://WWW.FCBARCELONA.COM/report.pdf?utm_source=x#page=2",
            "https://www.fcbarcelona.com/report.pdf",
        ),
        (
            "https://example.test/report.pdf?b=2&a=1&fbclid=x",
            "https://example.test/report.pdf?a=1&b=2",
        ),
    ],
)
def test_canonicalize_url_removes_tracking_and_fragment(source, expected):
    assert canonicalize_url(source) == expected


def test_run_search_persists_raw_normalizes_deduplicates_and_filters(tmp_path):
    config_path = tmp_path / "search.json"
    _write_config(config_path)
    config = load_search_config(config_path)
    responses = {
        "Barcelona 2015 PDF": {
            "success": True,
            "data": {
                "web": [
                    {
                        "url": "https://www.fcbarcelona.com/report.pdf?utm_source=x",
                        "title": "Official report",
                        "description": "2015",
                        "category": "pdf",
                    },
                    {
                        "url": "https://unapproved.test/report.pdf",
                        "title": "Mirror",
                    },
                ]
            },
        },
        "Barcelona 2016 PDF": {
            "success": True,
            "data": {
                "web": [
                    {
                        "url": "https://www.fcbarcelona.com/report.pdf#download",
                        "title": "Duplicate",
                    },
                    {
                        "url": "https://example.test/not-a-pdf",
                        "title": "HTML page",
                    },
                    {
                        "url": "https://example.test/other.pdf",
                        "title": "Wrong PDF",
                    },
                ]
            },
        },
    }

    class StubClient:
        def search(self, query, **kwargs):
            assert kwargs == {"limit": 20, "country": "ES", "require_pdf": True}
            return responses[query]

    run_dir = tmp_path / "run"
    summary = run_evidence_search(
        config,
        StubClient(),
        run_dir,
        retrieved_at="2026-08-31T00:00:00Z",
    )

    assert summary == {"valid": True, "accepted": 1, "rejected": 3, "total": 4}
    assert read_accepted_urls(run_dir / "evidence.jsonl") == {
        "https://www.fcbarcelona.com/report.pdf"
    }
    records = [
        json.loads(line)
        for line in (run_dir / "evidence.jsonl").read_text().splitlines()
    ]
    accepted = next(row for row in records if row["decision"] == "accepted")
    assert accepted["query_ids"] == ["season-2015", "season-2016"]
    assert (run_dir / "raw" / "season-2015.json").is_file()
    assert json.loads((run_dir / "request.json").read_text()) == {
        "schema_version": 1,
        "queries": [
            {"id": "season-2015", "query": "Barcelona 2015 PDF"},
            {"id": "season-2016", "query": "Barcelona 2016 PDF"},
        ],
        "limit": 20,
        "country": "ES",
        "require_pdf": True,
    }
    assert json.loads((run_dir / "validation.json").read_text()) == summary

    replay_dir = tmp_path / "replay"
    replay_summary = replay_evidence_search(
        config,
        run_dir / "raw",
        replay_dir,
        retrieved_at="2026-08-31T00:00:00Z",
    )
    assert replay_summary == summary
    assert (replay_dir / "evidence.jsonl").read_text() == (
        run_dir / "evidence.jsonl"
    ).read_text()

    with pytest.raises(EvidenceSearchError, match="request does not match"):
        replay_evidence_search(
            replace(config, country="US"),
            run_dir / "raw",
            tmp_path / "invalid-replay",
        )


def test_run_search_preserves_malformed_provider_response_before_failing(tmp_path):
    config_path = tmp_path / "search.json"
    _write_config(config_path)

    class StubClient:
        def search(self, query, **kwargs):
            return {"success": False, "error": "provider unavailable"}

    run_dir = tmp_path / "run"
    with pytest.raises(EvidenceSearchError, match="provider search failed"):
        run_evidence_search(load_search_config(config_path), StubClient(), run_dir)

    assert (run_dir / "raw" / "season-2015.json").is_file()


def test_run_search_identifies_the_query_when_transport_fails(tmp_path):
    config_path = tmp_path / "search.json"
    _write_config(config_path)

    class StubClient:
        def search(self, query, **kwargs):
            raise EvidenceSearchError("HTTP 403: account disabled")

    with pytest.raises(
        EvidenceSearchError,
        match="query season-2015 failed: HTTP 403: account disabled",
    ):
        run_evidence_search(
            load_search_config(config_path), StubClient(), tmp_path / "run"
        )


def test_search_config_rejects_unnecessary_or_conflicting_fields(tmp_path):
    path = tmp_path / "search.json"
    _write_config(path)
    value = json.loads(path.read_text())
    value["provider"] = "generic"
    path.write_text(json.dumps(value))

    with pytest.raises(EvidenceSearchError, match="unsupported fields"):
        load_search_config(path)
