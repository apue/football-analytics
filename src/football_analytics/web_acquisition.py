"""Provider-neutral primitives for auditable web-data acquisition."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class AcquisitionError(RuntimeError):
    """Base error for configuration and acquisition contract failures."""


class FirecrawlDocumentError(AcquisitionError):
    """Raised when a Firecrawl response does not contain a valid target page."""


@dataclass(frozen=True)
class KeyPoolConfig:
    """KeyPool connection settings with a redacted representation."""

    base_url: str
    api_key: str = field(repr=False)


@dataclass(frozen=True)
class ContentContract:
    """Minimum observable evidence required before a page can be parsed."""

    required_text: tuple[str, ...] = ()
    min_profile_links: int = 0


@dataclass(frozen=True)
class FileContract:
    """Minimum target evidence required for a downloaded binary file."""

    content_types: tuple[str, ...] = ()
    magic_prefix: bytes = b""
    tail_marker: bytes = b""
    min_bytes: int = 1


@dataclass(frozen=True)
class ValidatedDocument:
    """Validated content extracted from a provider response."""

    content: str
    content_format: str
    target_status: int
    content_sha256: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class AcquisitionResult:
    """Auditable result for one manifest item."""

    item_id: str
    url: str
    provider: str
    status: str
    transport_status: str
    provider_status: str
    cache_state: str
    attempt: int
    retrieved_at: str
    raw_path: Path
    content_path: Path | None
    target_status: int | None
    content_sha256: str | None
    error_classification: str | None
    cost: float | None
    error: str | None


@dataclass(frozen=True)
class BatchAcquisitionResult:
    """Resumable state and item results for one Firecrawl batch."""

    status: str
    job_id: str | None
    attempt: int
    results: tuple[AcquisitionResult, ...]


RequestJson = Callable[
    [str, str, Mapping[str, str], Mapping[str, Any] | None], Mapping[str, Any]
]


class FirecrawlClient:
    """Minimal Firecrawl v2 client routed through a KeyPool base URL."""

    def __init__(
        self,
        config: KeyPoolConfig,
        *,
        request_json: RequestJson | None = None,
    ) -> None:
        self._config = config
        self._request_json = request_json or _request_json

    def scrape(
        self, url: str, *, formats: tuple[str, ...] = ("rawHtml", "markdown")
    ) -> Mapping[str, Any]:
        """Scrape one known URL and return the unmodified provider payload."""

        return self._request_json(
            "POST",
            f"{self._config.base_url}/v2/scrape",
            {
                "Authorization": f"Bearer {self._config.api_key}",
                "x-keypool-service": "firecrawl",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
            {
                "url": url,
                "formats": list(formats),
                "onlyMainContent": True,
            },
        )

    def start_batch(
        self,
        urls: Iterable[str],
        *,
        formats: tuple[str, ...] = ("rawHtml", "markdown"),
        max_concurrency: int | None = None,
    ) -> str:
        """Start an asynchronous Firecrawl batch for known URLs."""

        response = self.start_batch_job(
            urls,
            formats=formats,
            max_concurrency=max_concurrency,
        )
        return str(response["id"])

    def start_batch_job(
        self,
        urls: Iterable[str],
        *,
        formats: tuple[str, ...] = ("rawHtml", "markdown"),
        max_concurrency: int | None = None,
    ) -> Mapping[str, Any]:
        """Start a batch and require a provider-confirmed job identifier."""

        response = self.start_batch_request(
            urls,
            formats=formats,
            max_concurrency=max_concurrency,
        )
        job_id = response.get("id")
        if response.get("success") is not True or not isinstance(job_id, str):
            raise AcquisitionError("Firecrawl batch did not return a job id")
        return response

    def start_batch_request(
        self,
        urls: Iterable[str],
        *,
        formats: tuple[str, ...] = ("rawHtml", "markdown"),
        max_concurrency: int | None = None,
    ) -> Mapping[str, Any]:
        """Start a batch and return the unmodified provider response."""

        payload: dict[str, Any] = {
            "urls": list(urls),
            "formats": list(formats),
            "onlyMainContent": True,
        }
        if max_concurrency is not None:
            payload["maxConcurrency"] = max_concurrency
        return self._request_json(
            "POST",
            f"{self._config.base_url}/v2/batch/scrape",
            self._headers(),
            payload,
        )

    def batch_status(self, job_id: str) -> Mapping[str, Any]:
        """Read one batch status page through the same KeyPool route."""

        return self._request_json(
            "GET",
            f"{self._config.base_url}/v2/batch/scrape/{job_id}",
            self._headers(),
            None,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.api_key}",
            "x-keypool-service": "firecrawl",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }


def load_keypool_config(path: Path) -> KeyPoolConfig:
    """Load KeyPool settings from a dotenv-style file without logging values."""

    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    api_key = values.get("KEYPOOL_KEY", "")
    base_url = _normalize_base_url(values.get("KEYPOOL_URL", ""))
    if not api_key:
        raise AcquisitionError("KEYPOOL_KEY is missing or empty")
    return KeyPoolConfig(base_url=base_url, api_key=api_key)


def validate_firecrawl_document(
    payload: Mapping[str, Any], contract: ContentContract
) -> ValidatedDocument:
    """Validate transport-independent Firecrawl content and target evidence."""

    if payload.get("success") is not True:
        raise FirecrawlDocumentError("firecrawl_success=false")

    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise FirecrawlDocumentError("firecrawl_data=missing")
    metadata = data.get("metadata")
    if not isinstance(metadata, Mapping):
        metadata = {}
    target_status = metadata.get("statusCode")
    if not isinstance(target_status, int) or not 200 <= target_status < 300:
        raise FirecrawlDocumentError(f"target_status={target_status}")

    content_format, content = _document_content(data)
    if not content:
        raise FirecrawlDocumentError("content=empty")
    missing = [text for text in contract.required_text if text not in content]
    if missing:
        raise FirecrawlDocumentError(f"required_text_missing={missing!r}")
    profile_links = content.count("/profil/spieler/")
    if profile_links < contract.min_profile_links:
        raise FirecrawlDocumentError(
            f"profile_links={profile_links} minimum={contract.min_profile_links}"
        )

    return ValidatedDocument(
        content=content,
        content_format=content_format,
        target_status=target_status,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        metadata=metadata,
    )


def build_manifest(
    items: Iterable[Mapping[str, Any]], *, provider: str
) -> list[dict[str, Any]]:
    """Build a stable, URL-deduplicated acquisition manifest."""

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        url = str(item.get("url", "")).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        row = dict(item)
        row.update(
            {
                "item_id": hashlib.sha256(f"{provider}\0{url}".encode()).hexdigest()[
                    :20
                ],
                "provider": provider,
                "status": "pending",
            }
        )
        rows.append(row)
    return rows


def acquire_firecrawl_batch(
    client: Any,
    items: Iterable[Mapping[str, Any]],
    run_dir: Path,
    contracts: Mapping[str, ContentContract],
    *,
    max_concurrency: int | None = None,
) -> BatchAcquisitionResult:
    """Start or resume one batch and validate every completed target item."""

    item_rows = list(items)
    fingerprint = hashlib.sha256(
        "\0".join(sorted(str(item["item_id"]) for item in item_rows)).encode()
    ).hexdigest()[:20]
    job_path = run_dir / "batches" / f"{fingerprint}.json"
    previous = json.loads(job_path.read_text()) if job_path.exists() else {}
    raw_dir = run_dir / "raw" / "firecrawl-batch" / fingerprint

    class PayloadClient:
        def __init__(self, value: Mapping[str, Any]) -> None:
            self.value = value

        def scrape(self, _url: str, *, formats: tuple[str, ...]) -> Mapping[str, Any]:
            return self.value

    cached_by_id: dict[str, AcquisitionResult] = {}
    pending = []
    for item in item_rows:
        item_id = str(item["item_id"])
        record_path = run_dir / "records" / f"{item_id}.json"
        if record_path.exists():
            existing = _result_from_record(
                record_path, json.loads(record_path.read_text())
            )
            if existing.status != "retryable_failed":
                cached_by_id[item_id] = replace(existing, cache_state="hit")
                continue
        pending.append(item)

    if not pending:
        return BatchAcquisitionResult(
            str(previous.get("status", "completed")),
            str(previous["job_id"]) if previous.get("job_id") else None,
            int(previous.get("attempt", 0)),
            tuple(cached_by_id[str(item["item_id"])] for item in item_rows),
        )

    active = previous.get("status") in {"queued", "processing"}
    attempt = (
        int(previous.get("attempt", 0))
        if active
        else int(previous.get("attempt", 0)) + 1
    )
    job_raw_paths = list(previous.get("raw_paths", []))

    def persist_batch_exception(
        exc: Exception, stage: str, current_job_id: str | None
    ) -> BatchAcquisitionResult:
        retrieved_at = datetime.now(UTC).isoformat()
        error_path = raw_dir / f"attempt-{attempt:03d}-{stage}.error.json"
        results = []
        for item in pending:
            item_id = str(item["item_id"])
            result = _transport_failure(
                item_id,
                str(item["url"]),
                str(item.get("provider", "firecrawl")),
                attempt,
                retrieved_at,
                error_path,
                exc,
                http_error_layer="provider",
            )
            record_path = run_dir / "records" / f"{item_id}.json"
            _write_json(record_path, _result_record(result, record_path))
            results.append(result)
        classification = results[0].error_classification if results else None
        _write_json(
            error_path,
            {
                "error_type": type(exc).__name__,
                "classification": classification,
            },
        )
        failure_raw_paths = list(job_raw_paths)
        failure_raw_paths.append(str(error_path.relative_to(run_dir)))
        _write_json(
            job_path,
            {
                "job_id": current_job_id,
                "status": "failed",
                "attempt": attempt,
                "item_ids": [str(item["item_id"]) for item in pending],
                "urls": [str(item["url"]) for item in pending],
                "started_at": retrieved_at,
                "raw_paths": failure_raw_paths,
                "cost": None,
                "error_classification": classification,
            },
        )
        return BatchAcquisitionResult("failed", current_job_id, attempt, tuple(results))

    if active:
        job_id = str(previous["job_id"])
        job = dict(previous)
    else:
        try:
            start_payload = client.start_batch_request(
                [str(item["url"]) for item in pending],
                formats=("rawHtml", "markdown"),
                max_concurrency=max_concurrency,
            )
        except Exception as exc:
            return persist_batch_exception(exc, "start", None)
        start_path = raw_dir / f"attempt-{attempt:03d}-start.json"
        _write_json(start_path, start_payload)
        job_raw_paths = [str(start_path.relative_to(run_dir))]
        job_id_value = start_payload.get("id")
        if start_payload.get("success") is not True or not isinstance(
            job_id_value, str
        ):
            failed_results = dict(cached_by_id)
            for item in pending:
                item_id = str(item["item_id"])
                failed_results[item_id] = acquire_firecrawl_item(
                    PayloadClient(start_payload),
                    item,
                    run_dir,
                    contracts.get(item_id, ContentContract()),
                )
            _write_json(
                job_path,
                {
                    "job_id": None,
                    "status": "failed",
                    "attempt": attempt,
                    "item_ids": [str(item["item_id"]) for item in pending],
                    "urls": [str(item["url"]) for item in pending],
                    "started_at": datetime.now(UTC).isoformat(),
                    "raw_paths": job_raw_paths,
                    "cost": _provider_cost(start_payload),
                    "error_classification": "provider_response",
                },
            )
            return BatchAcquisitionResult(
                "failed",
                None,
                attempt,
                tuple(failed_results[str(item["item_id"])] for item in item_rows),
            )
        job_id = job_id_value
        job = {
            "job_id": job_id,
            "status": "queued",
            "attempt": attempt,
            "item_ids": [str(item["item_id"]) for item in pending],
            "urls": [str(item["url"]) for item in pending],
            "started_at": datetime.now(UTC).isoformat(),
            "raw_paths": job_raw_paths,
            "cost": None,
        }
        _write_json(job_path, job)

    try:
        status_payload = client.batch_status(job_id)
    except Exception as exc:
        return persist_batch_exception(exc, "status", job_id)
    poll = len(list(raw_dir.glob(f"attempt-{attempt:03d}-status-*.json"))) + 1
    status_path = raw_dir / f"attempt-{attempt:03d}-status-{poll:03d}.json"
    _write_json(status_path, status_payload)
    status = str(status_payload.get("status", "failed"))
    raw_paths = list(job.get("raw_paths", []))
    raw_paths.append(str(status_path.relative_to(run_dir)))
    job.update(
        {
            "status": status,
            "raw_paths": raw_paths,
            "cost": _provider_cost(status_payload),
        }
    )
    _write_json(job_path, job)

    if status != "completed":
        if status in {"queued", "processing"}:
            return BatchAcquisitionResult(
                status,
                job_id,
                attempt,
                tuple(
                    cached_by_id[str(item["item_id"])]
                    for item in item_rows
                    if str(item["item_id"]) in cached_by_id
                ),
            )
        failed_results = dict(cached_by_id)
        failure_payload = {
            "success": False,
            "error": f"batch_status={status}",
        }
        for item in pending:
            item_id = str(item["item_id"])
            failed_results[item_id] = acquire_firecrawl_item(
                PayloadClient(failure_payload),
                item,
                run_dir,
                contracts.get(item_id, ContentContract()),
            )
        return BatchAcquisitionResult(
            status,
            job_id,
            attempt,
            tuple(failed_results[str(item["item_id"])] for item in item_rows),
        )

    documents = status_payload.get("data")
    if not isinstance(documents, list):
        documents = []
    documents_by_url = {}
    for document in documents:
        if not isinstance(document, Mapping):
            continue
        metadata = document.get("metadata")
        if not isinstance(metadata, Mapping):
            continue
        source_url = metadata.get("sourceURL", metadata.get("url"))
        if isinstance(source_url, str):
            documents_by_url[source_url] = document

    results_by_id = dict(cached_by_id)

    for item in pending:
        item_id = str(item["item_id"])
        document = documents_by_url.get(str(item["url"]))
        payload: Mapping[str, Any]
        if document is None:
            payload = {"success": False, "error": "batch_result_missing"}
        else:
            payload = {"success": True, "data": document}

        results_by_id[item_id] = acquire_firecrawl_item(
            PayloadClient(payload),
            item,
            run_dir,
            contracts.get(item_id, ContentContract()),
        )
    return BatchAcquisitionResult(
        status,
        job_id,
        attempt,
        tuple(results_by_id[str(item["item_id"])] for item in item_rows),
    )


def acquire_firecrawl_item(
    client: Any,
    item: Mapping[str, Any],
    run_dir: Path,
    contract: ContentContract,
) -> AcquisitionResult:
    """Acquire one item, preserve every raw attempt, and cache success."""

    item_id = str(item["item_id"])
    url = str(item["url"])
    provider = str(item.get("provider", "firecrawl"))
    record_path = run_dir / "records" / f"{item_id}.json"
    if record_path.exists():
        existing = _result_from_record(record_path, json.loads(record_path.read_text()))
        if existing.status != "retryable_failed":
            return replace(existing, cache_state="hit")

    attempt_dir = run_dir / "raw" / provider / item_id
    attempt = len(list(attempt_dir.glob("attempt-*.json"))) + 1
    raw_path = attempt_dir / f"attempt-{attempt:03d}.json"
    retrieved_at = datetime.now(UTC).isoformat()
    try:
        payload = client.scrape(url, formats=("rawHtml", "markdown"))
    except Exception as exc:
        error_path = attempt_dir / f"attempt-{attempt:03d}.error.json"
        result = _transport_failure(
            item_id,
            url,
            provider,
            attempt,
            retrieved_at,
            error_path,
            exc,
            http_error_layer="provider",
        )
        _write_json(
            error_path,
            {
                "error_type": type(exc).__name__,
                "classification": result.error_classification,
            },
        )
        _write_json(record_path, _result_record(result, record_path))
        return result
    _write_json(raw_path, payload)

    try:
        document = validate_firecrawl_document(payload, contract)
    except FirecrawlDocumentError as exc:
        error_classification = _firecrawl_error_classification(payload)
        result = AcquisitionResult(
            item_id=item_id,
            url=url,
            provider=provider,
            status=(
                "retryable_failed"
                if error_classification == "target_transient"
                else "validation_failed"
            ),
            transport_status="passed",
            provider_status=("passed" if payload.get("success") is True else "failed"),
            cache_state="miss",
            attempt=attempt,
            retrieved_at=retrieved_at,
            raw_path=raw_path,
            content_path=None,
            target_status=_target_status(payload),
            content_sha256=None,
            error_classification=error_classification,
            cost=_provider_cost(payload),
            error=str(exc),
        )
    else:
        content_path = run_dir / "content" / f"{item_id}.{document.content_format}"
        _write_text(content_path, document.content)
        result = AcquisitionResult(
            item_id=item_id,
            url=url,
            provider=provider,
            status="complete",
            transport_status="passed",
            provider_status="passed",
            cache_state="miss",
            attempt=attempt,
            retrieved_at=retrieved_at,
            raw_path=raw_path,
            content_path=content_path,
            target_status=document.target_status,
            content_sha256=document.content_sha256,
            error_classification=None,
            cost=_provider_cost(payload),
            error=None,
        )

    _write_json(record_path, _result_record(result, record_path))
    return result


def acquire_http_file_item(
    download: Callable[[str], tuple[int, str, bytes]],
    item: Mapping[str, Any],
    run_dir: Path,
    contract: FileContract,
) -> AcquisitionResult:
    """Download and validate one binary source while preserving raw evidence."""

    item_id = str(item["item_id"])
    url = str(item["url"])
    provider = str(item.get("provider", "http-file"))
    record_path = run_dir / "records" / f"{item_id}.json"
    if record_path.exists():
        existing = _result_from_record(record_path, json.loads(record_path.read_text()))
        if existing.status != "retryable_failed":
            return replace(existing, cache_state="hit")

    attempt_dir = run_dir / "raw" / provider / item_id
    attempt = len(list(attempt_dir.glob("attempt-*"))) + 1
    suffix = Path(urlparse(url).path).suffix or ".bin"
    raw_path = attempt_dir / f"attempt-{attempt:03d}{suffix}"
    retrieved_at = datetime.now(UTC).isoformat()
    try:
        status, content_type, body = download(url)
    except Exception as exc:
        error_path = attempt_dir / f"attempt-{attempt:03d}.error.json"
        result = _transport_failure(
            item_id,
            url,
            provider,
            attempt,
            retrieved_at,
            error_path,
            exc,
            http_error_layer="target",
        )
        _write_json(
            error_path,
            {
                "error_type": type(exc).__name__,
                "classification": result.error_classification,
            },
        )
        _write_json(record_path, _result_record(result, record_path))
        return result
    _write_bytes(raw_path, body)

    errors = []
    if not 200 <= status < 300:
        errors.append(f"target_status={status}")
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if contract.content_types and normalized_type not in contract.content_types:
        errors.append(f"content_type={normalized_type or 'missing'}")
    if contract.magic_prefix and not body.startswith(contract.magic_prefix):
        errors.append("magic_prefix=missing")
    if contract.tail_marker and contract.tail_marker not in body[-2048:]:
        errors.append("tail_marker=missing")
    if len(body) < contract.min_bytes:
        errors.append(f"content_bytes={len(body)} minimum={contract.min_bytes}")

    error_classification = _target_error_classification(status) if errors else None
    result = AcquisitionResult(
        item_id=item_id,
        url=url,
        provider=provider,
        status=(
            "retryable_failed"
            if error_classification == "target_transient"
            else "validation_failed"
            if errors
            else "complete"
        ),
        transport_status="passed",
        provider_status="passed",
        cache_state="miss",
        attempt=attempt,
        retrieved_at=retrieved_at,
        raw_path=raw_path,
        content_path=None if errors else raw_path,
        target_status=status,
        content_sha256=hashlib.sha256(body).hexdigest() if not errors else None,
        error_classification=error_classification,
        cost=None,
        error="; ".join(errors) if errors else None,
    )
    _write_json(record_path, _result_record(result, record_path))
    return result


def download_http_file(url: str) -> tuple[int, str, bytes]:
    """Download one public file with a conventional browser user agent."""

    request = Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=120) as response:
        return (
            response.status,
            response.headers.get("Content-Type", ""),
            response.read(),
        )


def _normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value:
        raise AcquisitionError("KEYPOOL_URL is missing or empty")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    parsed = urlparse(value)
    if not parsed.hostname:
        raise AcquisitionError("KEYPOOL_URL is not a valid base URL")
    return value


def _document_content(data: Mapping[str, Any]) -> tuple[str, str]:
    for key in ("rawHtml", "html", "markdown"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return key, value
    return "", ""


def _request_json(
    method: str,
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    request = Request(
        url,
        method=method,
        headers=dict(headers),
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    with urlopen(request, timeout=120) as response:
        value = json.loads(response.read())
    if not isinstance(value, Mapping):
        raise AcquisitionError("provider response must be a JSON object")
    return value


def _target_status(payload: Mapping[str, Any]) -> int | None:
    data = payload.get("data")
    if not isinstance(data, Mapping):
        return None
    metadata = data.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    value = metadata.get("statusCode")
    return value if isinstance(value, int) else None


def _target_error_classification(status: int) -> str:
    if status in {408, 429} or status >= 500:
        return "target_transient"
    if not 200 <= status < 300:
        return "target_permanent"
    return "content_contract"


def _firecrawl_error_classification(payload: Mapping[str, Any]) -> str:
    if payload.get("success") is not True:
        return "provider_response"
    target_status = _target_status(payload)
    if target_status is not None and not 200 <= target_status < 300:
        return _target_error_classification(target_status)
    return "content_contract"


def _transport_failure(
    item_id: str,
    url: str,
    provider: str,
    attempt: int,
    retrieved_at: str,
    raw_path: Path,
    exc: Exception,
    *,
    http_error_layer: str,
) -> AcquisitionResult:
    target_status = exc.code if isinstance(exc, HTTPError) else None
    if target_status is None:
        error_classification = "transport_transient"
        provider_status = "not_checked"
    elif http_error_layer == "provider":
        error_classification = (
            "provider_transient"
            if target_status in {408, 429} or target_status >= 500
            else "provider_permanent"
        )
        provider_status = "failed"
        target_status = None
    else:
        error_classification = _target_error_classification(target_status)
        provider_status = "passed"
    return AcquisitionResult(
        item_id=item_id,
        url=url,
        provider=provider,
        status=(
            "retryable_failed"
            if error_classification
            in {"target_transient", "provider_transient", "transport_transient"}
            else "validation_failed"
        ),
        transport_status=("passed" if isinstance(exc, HTTPError) else "failed"),
        provider_status=provider_status,
        cache_state="miss",
        attempt=attempt,
        retrieved_at=retrieved_at,
        raw_path=raw_path,
        content_path=None,
        target_status=target_status,
        content_sha256=None,
        error_classification=error_classification,
        cost=None,
        error=type(exc).__name__,
    )


def _result_record(result: AcquisitionResult, record_path: Path) -> dict[str, Any]:
    root = record_path.parent.parent
    return {
        "item_id": result.item_id,
        "url": result.url,
        "provider": result.provider,
        "status": result.status,
        "transport_status": result.transport_status,
        "provider_status": result.provider_status,
        "cache_state": result.cache_state,
        "attempt": result.attempt,
        "retrieved_at": result.retrieved_at,
        "raw_path": str(result.raw_path.relative_to(root)),
        "content_path": (
            str(result.content_path.relative_to(root)) if result.content_path else None
        ),
        "target_status": result.target_status,
        "content_sha256": result.content_sha256,
        "error_classification": result.error_classification,
        "cost": result.cost,
        "error": result.error,
    }


def _result_from_record(
    record_path: Path, record: Mapping[str, Any]
) -> AcquisitionResult:
    root = record_path.parent.parent
    content_value = record.get("content_path")
    return AcquisitionResult(
        item_id=str(record["item_id"]),
        url=str(record["url"]),
        provider=str(record["provider"]),
        status=str(record["status"]),
        transport_status=str(record.get("transport_status", "not_recorded")),
        provider_status=str(record.get("provider_status", "not_recorded")),
        cache_state=str(record.get("cache_state", "not_recorded")),
        attempt=int(record["attempt"]),
        retrieved_at=str(record["retrieved_at"]),
        raw_path=root / str(record["raw_path"]),
        content_path=root / str(content_value) if content_value else None,
        target_status=(
            int(record["target_status"])
            if isinstance(record.get("target_status"), int)
            else None
        ),
        content_sha256=(
            str(record["content_sha256"]) if record.get("content_sha256") else None
        ),
        error_classification=(
            str(record["error_classification"])
            if record.get("error_classification")
            else None
        ),
        cost=(
            float(record["cost"])
            if isinstance(record.get("cost"), (int, float))
            and not isinstance(record.get("cost"), bool)
            else None
        ),
        error=str(record["error"]) if record.get("error") else None,
    )


def _provider_cost(payload: Mapping[str, Any]) -> float | None:
    for key in ("creditsUsed", "credits_used", "cost"):
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, encoding="utf-8", delete=False
    ) as handle:
        handle.write(value)
        temporary = Path(handle.name)
    temporary.replace(path)


def _write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(value)
        temporary = Path(handle.name)
    temporary.replace(path)
