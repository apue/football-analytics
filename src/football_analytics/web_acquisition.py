"""Provider-neutral primitives for auditable web-data acquisition."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
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
    attempt: int
    retrieved_at: str
    raw_path: Path
    content_path: Path | None
    target_status: int | None
    content_sha256: str | None
    error: str | None


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

        payload: dict[str, Any] = {
            "urls": list(urls),
            "formats": list(formats),
            "onlyMainContent": True,
        }
        if max_concurrency is not None:
            payload["maxConcurrency"] = max_concurrency
        response = self._request_json(
            "POST",
            f"{self._config.base_url}/v2/batch/scrape",
            self._headers(),
            payload,
        )
        job_id = response.get("id")
        if response.get("success") is not True or not isinstance(job_id, str):
            raise AcquisitionError("Firecrawl batch did not return a job id")
        return job_id

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
        if existing.status == "complete":
            return existing

    attempt_dir = run_dir / "raw" / provider / item_id
    attempt = len(list(attempt_dir.glob("attempt-*.json"))) + 1
    raw_path = attempt_dir / f"attempt-{attempt:03d}.json"
    retrieved_at = datetime.now(UTC).isoformat()
    try:
        payload = client.scrape(url, formats=("rawHtml", "markdown"))
    except Exception as exc:
        error_path = attempt_dir / f"attempt-{attempt:03d}.error.json"
        result = _transport_failure(
            item_id, url, provider, attempt, retrieved_at, error_path, exc
        )
        _write_json(
            error_path,
            {"error_type": type(exc).__name__, "classification": result.status},
        )
        _write_json(record_path, _result_record(result, record_path))
        return result
    _write_json(raw_path, payload)

    try:
        document = validate_firecrawl_document(payload, contract)
    except FirecrawlDocumentError as exc:
        result = AcquisitionResult(
            item_id=item_id,
            url=url,
            provider=provider,
            status="validation_failed",
            attempt=attempt,
            retrieved_at=retrieved_at,
            raw_path=raw_path,
            content_path=None,
            target_status=_target_status(payload),
            content_sha256=None,
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
            attempt=attempt,
            retrieved_at=retrieved_at,
            raw_path=raw_path,
            content_path=content_path,
            target_status=document.target_status,
            content_sha256=document.content_sha256,
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
        if existing.status == "complete":
            return existing

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
            item_id, url, provider, attempt, retrieved_at, error_path, exc
        )
        _write_json(
            error_path,
            {"error_type": type(exc).__name__, "classification": result.status},
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

    result = AcquisitionResult(
        item_id=item_id,
        url=url,
        provider=provider,
        status="validation_failed" if errors else "complete",
        attempt=attempt,
        retrieved_at=retrieved_at,
        raw_path=raw_path,
        content_path=None if errors else raw_path,
        target_status=status,
        content_sha256=hashlib.sha256(body).hexdigest() if not errors else None,
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


def _transport_failure(
    item_id: str,
    url: str,
    provider: str,
    attempt: int,
    retrieved_at: str,
    raw_path: Path,
    exc: Exception,
) -> AcquisitionResult:
    return AcquisitionResult(
        item_id=item_id,
        url=url,
        provider=provider,
        status="retryable_failed",
        attempt=attempt,
        retrieved_at=retrieved_at,
        raw_path=raw_path,
        content_path=None,
        target_status=None,
        content_sha256=None,
        error=type(exc).__name__,
    )


def _result_record(result: AcquisitionResult, record_path: Path) -> dict[str, Any]:
    root = record_path.parent.parent
    return {
        "item_id": result.item_id,
        "url": result.url,
        "provider": result.provider,
        "status": result.status,
        "attempt": result.attempt,
        "retrieved_at": result.retrieved_at,
        "raw_path": str(result.raw_path.relative_to(root)),
        "content_path": (
            str(result.content_path.relative_to(root)) if result.content_path else None
        ),
        "target_status": result.target_status,
        "content_sha256": result.content_sha256,
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
        error=str(record["error"]) if record.get("error") else None,
    )


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
