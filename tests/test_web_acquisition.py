import json
from urllib.error import HTTPError

import pytest

from football_analytics.web_acquisition import (
    AcquisitionResult,
    ContentContract,
    FileContract,
    FirecrawlClient,
    FirecrawlDocumentError,
    KeyPoolConfig,
    acquire_firecrawl_batch,
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


def test_firecrawl_batch_is_persisted_resumable_and_validates_each_item(tmp_path):
    class StubClient:
        def __init__(self):
            self.starts = 0
            self.polls = 0

        def start_batch_request(self, urls, *, formats, max_concurrency):
            self.starts += 1
            assert list(urls) == [
                "https://example.test/a",
                "https://example.test/b",
            ]
            assert max_concurrency == 2
            return {"success": True, "id": "job-123"}

        def batch_status(self, job_id):
            self.polls += 1
            assert job_id == "job-123"
            if self.polls == 1:
                return {"success": True, "status": "processing", "completed": 0}
            return {
                "success": True,
                "status": "completed",
                "creditsUsed": 2,
                "data": [
                    {
                        "markdown": "Academy A",
                        "metadata": {
                            "sourceURL": "https://example.test/a",
                            "statusCode": 200,
                        },
                    },
                    {
                        "markdown": "Academy B",
                        "metadata": {
                            "sourceURL": "https://example.test/b",
                            "statusCode": 200,
                        },
                    },
                ],
            }

    client = StubClient()
    items = [
        {
            "item_id": "a",
            "url": "https://example.test/a",
            "provider": "firecrawl",
        },
        {
            "item_id": "b",
            "url": "https://example.test/b",
            "provider": "firecrawl",
        },
    ]
    contracts = {
        "a": ContentContract(required_text=("Academy A",)),
        "b": ContentContract(required_text=("Academy B",)),
    }

    processing = acquire_firecrawl_batch(
        client, items, tmp_path, contracts, max_concurrency=2
    )
    completed = acquire_firecrawl_batch(
        client, items, tmp_path, contracts, max_concurrency=2
    )
    cached = acquire_firecrawl_batch(
        client, items, tmp_path, contracts, max_concurrency=2
    )

    assert processing.status == "processing"
    assert processing.results == ()
    assert completed.status == "completed"
    assert [result.status for result in completed.results] == ["complete", "complete"]
    assert cached.status == "completed"
    assert cached.job_id == "job-123"
    assert cached.attempt == 1
    assert all(result.cache_state == "hit" for result in cached.results)
    assert client.starts == 1
    assert client.polls == 2
    job = json.loads(next((tmp_path / "batches").glob("*.json")).read_text())
    assert job["status"] == "completed"
    assert job["attempt"] == 1
    assert job["cost"] == 2.0
    raw_paths = sorted((tmp_path / "raw/firecrawl-batch").rglob("*.json"))
    assert len(raw_paths) == 3
    assert (tmp_path / "records/a.json").exists()
    assert (tmp_path / "records/b.json").exists()


def test_firecrawl_batch_failure_writes_per_item_failure_records(tmp_path):
    class StubClient:
        def start_batch_request(self, urls, *, formats, max_concurrency):
            return {"success": True, "id": "job-failed"}

        def batch_status(self, _job_id):
            return {"success": False, "status": "failed", "error": "quota"}

    items = [
        {
            "item_id": "a",
            "url": "https://example.test/a",
            "provider": "firecrawl",
        }
    ]

    failed = acquire_firecrawl_batch(
        StubClient(), items, tmp_path, {"a": ContentContract()}
    )
    cached = acquire_firecrawl_batch(
        StubClient(), items, tmp_path, {"a": ContentContract()}
    )

    assert failed.status == "failed"
    assert len(failed.results) == 1
    assert failed.results[0].status == "validation_failed"
    assert failed.results[0].provider_status == "failed"
    assert failed.results[0].error_classification == "provider_response"
    assert cached.status == "failed"
    assert cached.job_id == "job-failed"
    assert cached.attempt == 1
    assert cached.results[0].cache_state == "hit"
    assert (tmp_path / "records/a.json").exists()


def test_firecrawl_batch_start_http_error_writes_provider_failure_records(tmp_path):
    class StubClient:
        def start_batch_request(self, urls, *, formats, max_concurrency):
            raise HTTPError("https://keypool.test/batch", 401, "Unauthorized", {}, None)

    items = [
        {
            "item_id": "a",
            "url": "https://example.test/a",
            "provider": "firecrawl",
        }
    ]

    failed = acquire_firecrawl_batch(
        StubClient(), items, tmp_path, {"a": ContentContract()}
    )

    assert failed.status == "failed"
    assert failed.job_id is None
    assert failed.results[0].status == "validation_failed"
    assert failed.results[0].provider_status == "failed"
    assert failed.results[0].target_status is None
    assert failed.results[0].error_classification == "provider_permanent"
    assert (tmp_path / "records/a.json").exists()
    assert next((tmp_path / "batches").glob("*.json")).exists()


def test_firecrawl_batch_invalid_start_payload_is_preserved_as_provider_failure(
    tmp_path,
):
    start_payload = {"success": False, "error": "invalid request", "creditsUsed": 1}

    class StubClient:
        def start_batch_request(self, urls, *, formats, max_concurrency):
            return start_payload

    items = [
        {
            "item_id": "a",
            "url": "https://example.test/a",
            "provider": "firecrawl",
        }
    ]

    failed = acquire_firecrawl_batch(
        StubClient(), items, tmp_path, {"a": ContentContract()}
    )
    cached = acquire_firecrawl_batch(
        StubClient(), items, tmp_path, {"a": ContentContract()}
    )

    assert failed.status == "failed"
    assert failed.results[0].status == "validation_failed"
    assert failed.results[0].provider_status == "failed"
    assert failed.results[0].error_classification == "provider_response"
    assert cached.status == "failed"
    raw_start = next((tmp_path / "raw/firecrawl-batch").rglob("*-start.json"))
    assert json.loads(raw_start.read_text()) == start_payload
    job = json.loads(next((tmp_path / "batches").glob("*.json")).read_text())
    assert job["error_classification"] == "provider_response"
    assert job["cost"] == 1.0


def test_firecrawl_permanent_target_failure_is_cached_without_retry(tmp_path):
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
    cached = acquire_firecrawl_item(StubClient(), item, tmp_path, contract)

    assert isinstance(failed, AcquisitionResult)
    assert failed.status == "validation_failed"
    assert failed.raw_path.exists()
    assert failed.target_status == 405
    assert failed.error_classification == "target_permanent"
    assert failed.cache_state == "miss"
    assert cached.status == "validation_failed"
    assert cached.cache_state == "hit"
    assert len(responses) == 1


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


def test_firecrawl_http_401_is_a_cached_provider_failure(tmp_path):
    calls = []

    class UnauthorizedClient:
        def scrape(self, url, *, formats):
            calls.append(url)
            raise HTTPError(url, 401, "Unauthorized", {}, None)

    item = {
        "item_id": "unauthorized",
        "url": "https://example.test/roster",
        "provider": "firecrawl",
    }

    failed = acquire_firecrawl_item(
        UnauthorizedClient(), item, tmp_path, ContentContract()
    )
    cached = acquire_firecrawl_item(
        UnauthorizedClient(), item, tmp_path, ContentContract()
    )

    assert failed.status == "validation_failed"
    assert failed.transport_status == "passed"
    assert failed.provider_status == "failed"
    assert failed.target_status is None
    assert failed.error_classification == "provider_permanent"
    assert cached.cache_state == "hit"
    assert calls == ["https://example.test/roster"]


def test_firecrawl_success_records_provider_cost_and_envelope(tmp_path):
    class StubClient:
        def scrape(self, _url, *, formats):
            return {
                "success": True,
                "creditsUsed": 2.5,
                "data": {
                    "markdown": "Academy roster",
                    "metadata": {"statusCode": 200},
                },
            }

    result = acquire_firecrawl_item(
        StubClient(),
        {
            "item_id": "costed",
            "url": "https://example.test/roster",
            "provider": "firecrawl",
        },
        tmp_path,
        ContentContract(required_text=("Academy roster",)),
    )

    assert result.status == "complete"
    assert result.transport_status == "passed"
    assert result.provider_status == "passed"
    assert result.cache_state == "miss"
    assert result.error_classification is None
    assert result.cost == 2.5
    record = json.loads((tmp_path / "records/costed.json").read_text())
    assert record["cost"] == 2.5


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
    assert first.transport_status == "passed"
    assert first.provider_status == "passed"
    assert first.cache_state == "miss"
    assert first.error_classification is None
    assert first.cost is None
    assert second.status == first.status
    assert second.content_path == first.content_path
    assert second.cache_state == "hit"
    assert calls == ["https://club.example.test/report.pdf"]
    record = json.loads((tmp_path / "records/annual-report-2019.json").read_text())
    assert record["transport_status"] == "passed"
    assert record["provider_status"] == "passed"
    assert record["cache_state"] == "miss"
    assert record["error_classification"] is None
    assert record["cost"] is None


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


def test_http_file_transient_503_is_retried(tmp_path):
    responses = [
        (503, "text/plain", b"unavailable"),
        (200, "application/pdf", b"%PDF-1.7\nfixture\n%%EOF\n"),
    ]

    def download(_url):
        return responses.pop(0)

    item = {
        "item_id": "temporarily-unavailable",
        "url": "https://club.example.test/report.pdf",
        "provider": "http-file",
    }
    contract = FileContract(
        content_types=("application/pdf",),
        magic_prefix=b"%PDF",
        tail_marker=b"%%EOF",
    )

    failed = acquire_http_file_item(download, item, tmp_path, contract)
    completed = acquire_http_file_item(download, item, tmp_path, contract)

    assert failed.status == "retryable_failed"
    assert failed.target_status == 503
    assert failed.error_classification == "target_transient"
    assert completed.status == "complete"
    assert responses == []


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


def test_http_file_permanent_404_is_cached_without_retry(tmp_path):
    calls = []

    def missing(url):
        calls.append(url)
        raise HTTPError(url, 404, "Not Found", {}, None)

    item = {
        "item_id": "missing-report",
        "url": "https://club.example.test/missing.pdf",
        "provider": "http-file",
    }

    failed = acquire_http_file_item(missing, item, tmp_path, FileContract())
    cached = acquire_http_file_item(missing, item, tmp_path, FileContract())

    assert failed.status == "validation_failed"
    assert failed.transport_status == "passed"
    assert failed.target_status == 404
    assert failed.error_classification == "target_permanent"
    assert cached.cache_state == "hit"
    assert calls == ["https://club.example.test/missing.pdf"]
