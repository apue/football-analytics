import json

import pytest

from football_analytics.web_acquisition import (
    AcquisitionResult,
    ContentContract,
    FileContract,
    FirecrawlClient,
    FirecrawlDocumentError,
    KeyPoolConfig,
    acquire_firecrawl_item,
    acquire_http_file_item,
    build_manifest,
    load_keypool_config,
    validate_firecrawl_document,
)


def test_keypool_config_normalizes_url_without_exposing_secret(tmp_path):
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "KEYPOOL_KEY=team-secret-value\nKEYPOOL_URL=keypool.example.test\n"
    )

    config = load_keypool_config(env_file)

    assert config.base_url == "https://keypool.example.test"
    assert config.api_key == "team-secret-value"
    assert "team-secret-value" not in repr(config)


def test_outer_success_with_failed_target_status_is_rejected():
    payload = {
        "success": True,
        "data": {
            "markdown": "Method Not Allowed",
            "metadata": {"statusCode": 405},
        },
    }

    with pytest.raises(FirecrawlDocumentError, match="target_status=405"):
        validate_firecrawl_document(payload, ContentContract())


def test_content_contract_requires_known_markers_and_profile_links():
    payload = {
        "success": True,
        "data": {
            "markdown": (
                "# FC Barcelona U19\n"
                "[A](/a/profil/spieler/1)\n"
                "[B](/b/profil/spieler/2)\n"
            ),
            "metadata": {"statusCode": 200},
        },
    }
    contract = ContentContract(
        required_text=("FC Barcelona U19",),
        min_profile_links=2,
    )

    document = validate_firecrawl_document(payload, contract)

    assert document.target_status == 200
    assert document.content_format == "markdown"
    assert document.content_sha256


def test_manifest_has_stable_ids_and_deduplicates_urls():
    rows = build_manifest(
        [
            {"url": "https://example.test/a", "page_type": "roster"},
            {"url": "https://example.test/a", "page_type": "roster"},
            {"url": "https://example.test/b", "page_type": "career"},
        ],
        provider="firecrawl",
    )

    assert len(rows) == 2
    assert rows[0]["item_id"] != rows[1]["item_id"]
    assert rows[0]["status"] == "pending"
    assert json.dumps(rows, sort_keys=True)


def test_firecrawl_client_uses_keypool_route_and_service_header():
    calls = []

    def request(method, url, headers, payload):
        calls.append((method, url, headers, payload))
        return {"success": True, "data": {"markdown": "ok"}}

    client = FirecrawlClient(
        KeyPoolConfig("https://keypool.example.test", "secret"),
        request_json=request,
    )

    client.scrape("https://example.test/page", formats=("markdown",))

    method, url, headers, payload = calls[0]
    assert method == "POST"
    assert url == "https://keypool.example.test/v2/scrape"
    assert headers["Authorization"] == "Bearer secret"
    assert headers["x-keypool-service"] == "firecrawl"
    assert payload == {
        "url": "https://example.test/page",
        "formats": ["markdown"],
        "onlyMainContent": True,
    }


def test_firecrawl_client_supports_batch_start_and_status():
    calls = []

    def request(method, url, headers, payload):
        calls.append((method, url, payload))
        if method == "POST":
            return {"success": True, "id": "job-123"}
        return {"success": True, "status": "completed", "data": []}

    client = FirecrawlClient(
        KeyPoolConfig("https://keypool.example.test", "secret"),
        request_json=request,
    )

    job_id = client.start_batch(["https://example.test/a", "https://example.test/b"])
    status = client.batch_status(job_id)

    assert job_id == "job-123"
    assert status["status"] == "completed"
    assert calls[0][:2] == (
        "POST",
        "https://keypool.example.test/v2/batch/scrape",
    )
    assert calls[1][:2] == (
        "GET",
        "https://keypool.example.test/v2/batch/scrape/job-123",
    )
    assert calls[1][2] is None


def test_acquisition_saves_raw_failure_and_reuses_completed_record(tmp_path):
    responses = [
        {
            "success": True,
            "data": {
                "markdown": "Method Not Allowed",
                "metadata": {"statusCode": 405},
            },
        },
        {
            "success": True,
            "data": {
                "markdown": "# Academy roster\n/player/profil/spieler/1",
                "metadata": {"statusCode": 200},
            },
        },
    ]

    class StubClient:
        def scrape(self, url, *, formats):
            return responses.pop(0)

    item = {
        "item_id": "roster-2019",
        "url": "https://example.test/roster",
        "provider": "firecrawl",
        "page_type": "roster",
    }
    contract = ContentContract(required_text=("Academy roster",), min_profile_links=1)

    failed = acquire_firecrawl_item(StubClient(), item, tmp_path, contract)
    completed = acquire_firecrawl_item(StubClient(), item, tmp_path, contract)
    cached = acquire_firecrawl_item(StubClient(), item, tmp_path, contract)

    assert isinstance(failed, AcquisitionResult)
    assert failed.status == "validation_failed"
    assert failed.raw_path.exists()
    assert completed.status == "complete"
    assert completed.content_path is not None
    assert completed.content_path.read_text().startswith("# Academy roster")
    assert cached == completed
    assert responses == []


def test_firecrawl_transport_failure_is_persisted_as_retryable(tmp_path):
    class FailingClient:
        def scrape(self, url, *, formats):
            raise TimeoutError("provider timed out")

    result = acquire_firecrawl_item(
        FailingClient(),
        {
            "item_id": "timeout",
            "url": "https://example.test/timeout",
            "provider": "firecrawl",
        },
        tmp_path,
        ContentContract(),
    )

    assert result.status == "retryable_failed"
    assert result.raw_path.exists()
    assert result.error == "TimeoutError"
    assert json.loads((tmp_path / "records/timeout.json").read_text())["status"] == (
        "retryable_failed"
    )


def test_http_file_provider_validates_pdf_and_caches_success(tmp_path):
    calls = []

    def download(url):
        calls.append(url)
        return 200, "application/pdf", b"%PDF-1.7\nfixture\n%%EOF\n"

    item = {
        "item_id": "annual-report-2019",
        "url": "https://club.example.test/report.pdf",
        "provider": "http-file",
    }

    first = acquire_http_file_item(
        download,
        item,
        tmp_path,
        FileContract(
            content_types=("application/pdf",),
            magic_prefix=b"%PDF",
            tail_marker=b"%%EOF",
        ),
    )
    second = acquire_http_file_item(
        download,
        item,
        tmp_path,
        FileContract(
            content_types=("application/pdf",),
            magic_prefix=b"%PDF",
            tail_marker=b"%%EOF",
        ),
    )

    assert first.status == "complete"
    assert first.content_path is not None
    assert first.content_path.read_bytes().startswith(b"%PDF")
    assert second == first
    assert calls == ["https://club.example.test/report.pdf"]


def test_http_file_provider_rejects_truncated_pdf(tmp_path):
    result = acquire_http_file_item(
        lambda _url: (200, "application/pdf", b"%PDF-incomplete"),
        {
            "item_id": "truncated",
            "url": "https://club.example.test/report.pdf",
            "provider": "http-file",
        },
        tmp_path,
        FileContract(magic_prefix=b"%PDF", tail_marker=b"%%EOF"),
    )

    assert result.status == "validation_failed"
    assert result.error == "tail_marker=missing"


def test_http_file_transport_failure_is_persisted_as_retryable(tmp_path):
    def fail(_url):
        raise ConnectionError("network unavailable")

    result = acquire_http_file_item(
        fail,
        {
            "item_id": "network-failure",
            "url": "https://club.example.test/report.pdf",
            "provider": "http-file",
        },
        tmp_path,
        FileContract(),
    )

    assert result.status == "retryable_failed"
    assert result.raw_path.suffix == ".json"
    assert result.raw_path.exists()
    assert result.error == "ConnectionError"
