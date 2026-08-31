"""Auditable direct Firecrawl search and evidence filtering."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from .evidence_bundle import canonicalize_url


class EvidenceSearchError(RuntimeError):
    """Raised when configuration, transport, or evidence contracts fail."""


@dataclass(frozen=True)
class FirecrawlConfig:
    """Firecrawl credentials whose representation never exposes the API key."""

    api_key: str = field(repr=False)


@dataclass(frozen=True)
class SearchQuery:
    """One stable query in an evidence search run."""

    query_id: str
    text: str


@dataclass(frozen=True)
class EvidenceSearchConfig:
    """The intentionally narrow configuration for one Firecrawl search run."""

    queries: tuple[SearchQuery, ...]
    limit: int
    country: str
    allowed_domains: tuple[str, ...]
    require_pdf: bool
    required_url_terms: tuple[str, ...]


RequestJson = Callable[
    [str, str, Mapping[str, str], Mapping[str, Any]], Mapping[str, Any]
]


class FirecrawlSearchClient:
    """Minimal direct Firecrawl v2 search client."""

    def __init__(
        self,
        config: FirecrawlConfig,
        *,
        request_json: RequestJson | None = None,
    ) -> None:
        self._config = config
        self._request_json = request_json or _request_json

    def search(
        self,
        query: str,
        *,
        limit: int,
        country: str,
        require_pdf: bool,
    ) -> Mapping[str, Any]:
        """Return an unmodified Firecrawl v2 web-search response."""

        payload: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "country": country,
            "sources": [{"type": "web"}],
        }
        if require_pdf:
            payload["categories"] = [{"type": "pdf"}]
        return self._request_json(
            "POST",
            "https://api.firecrawl.dev/v2/search",
            {
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "football-analytics-evidence-search/1",
            },
            payload,
        )


def load_firecrawl_config() -> FirecrawlConfig:
    """Load the direct Firecrawl API key from the process environment."""

    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        raise EvidenceSearchError("FIRECRAWL_API_KEY is missing or empty")
    return FirecrawlConfig(api_key)


def load_search_config(path: Path) -> EvidenceSearchConfig:
    """Load a strict version-one Firecrawl evidence-search configuration."""

    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSearchError(f"invalid search config {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceSearchError("search config must be a JSON object")
    allowed_fields = {
        "schema_version",
        "queries",
        "limit",
        "country",
        "allowed_domains",
        "require_pdf",
        "required_url_terms",
    }
    unsupported = sorted(set(value) - allowed_fields)
    if unsupported:
        raise EvidenceSearchError(f"unsupported fields: {unsupported}")
    if value.get("schema_version") != 1:
        raise EvidenceSearchError("schema_version must be 1")

    raw_queries = value.get("queries")
    if not isinstance(raw_queries, list) or not raw_queries:
        raise EvidenceSearchError("queries must be a non-empty list")
    queries: list[SearchQuery] = []
    seen_ids: set[str] = set()
    for raw in raw_queries:
        if not isinstance(raw, dict) or set(raw) != {"id", "query"}:
            raise EvidenceSearchError("each query must contain only id and query")
        query_id = _required_text(raw.get("id"), "queries[].id")
        text = _required_text(raw.get("query"), "queries[].query")
        if query_id in seen_ids:
            raise EvidenceSearchError(f"duplicate query id: {query_id}")
        seen_ids.add(query_id)
        queries.append(SearchQuery(query_id, text))

    limit = value.get("limit")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise EvidenceSearchError("limit must be an integer from 1 to 100")
    country = _required_text(value.get("country"), "country")
    raw_domains = value.get("allowed_domains")
    if not isinstance(raw_domains, list) or not raw_domains:
        raise EvidenceSearchError("allowed_domains must be a non-empty list")
    domains = tuple(_normalize_domain(item) for item in raw_domains)
    if len(set(domains)) != len(domains):
        raise EvidenceSearchError("allowed_domains must be unique")
    require_pdf = value.get("require_pdf")
    if not isinstance(require_pdf, bool):
        raise EvidenceSearchError("require_pdf must be a boolean")
    raw_terms = value.get("required_url_terms")
    if not isinstance(raw_terms, list) or not raw_terms:
        raise EvidenceSearchError("required_url_terms must be a non-empty list")
    terms = tuple(
        _required_text(item, "required_url_terms[]").casefold() for item in raw_terms
    )
    return EvidenceSearchConfig(
        tuple(queries), limit, country, domains, require_pdf, terms
    )


def run_evidence_search(
    config: EvidenceSearchConfig,
    client: FirecrawlSearchClient,
    output_dir: Path,
    *,
    retrieved_at: str | None = None,
) -> dict[str, int | bool]:
    """Execute all queries and write one deterministic, auditable evidence bundle."""

    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "request.json", _search_request_contract(config))
    responses = {}
    for query in config.queries:
        try:
            payload = client.search(
                query.text,
                limit=config.limit,
                country=config.country,
                require_pdf=config.require_pdf,
            )
        except EvidenceSearchError as exc:
            raise EvidenceSearchError(f"query {query.query_id} failed: {exc}") from exc
        _write_json(raw_dir / f"{query.query_id}.json", payload)
        responses[query.query_id] = payload
    return _write_evidence_bundle(
        config,
        responses,
        output_dir,
        retrieved_at=retrieved_at,
    )


def replay_evidence_search(
    config: EvidenceSearchConfig,
    raw_dir: Path,
    output_dir: Path,
    *,
    retrieved_at: str | None = None,
) -> dict[str, int | bool]:
    """Rebuild a bundle from preserved raw responses without network access."""

    request_path = raw_dir.parent / "request.json"
    try:
        request_contract = json.loads(request_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSearchError(
            f"invalid search request contract {request_path}: {exc}"
        ) from exc
    if request_contract != _search_request_contract(config):
        raise EvidenceSearchError("replay search request does not match current config")
    responses = {}
    for query in config.queries:
        path = raw_dir / f"{query.query_id}.json"
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise EvidenceSearchError(f"invalid raw response {path}: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise EvidenceSearchError(f"raw response must be an object: {path}")
        responses[query.query_id] = payload
    return _write_evidence_bundle(
        config,
        responses,
        output_dir,
        retrieved_at=retrieved_at,
    )


def _write_evidence_bundle(
    config: EvidenceSearchConfig,
    responses: Mapping[str, Mapping[str, Any]],
    output_dir: Path,
    *,
    retrieved_at: str | None,
) -> dict[str, int | bool]:
    timestamp = retrieved_at or datetime.now(UTC).isoformat()
    by_url: dict[str, dict[str, Any]] = {}
    for query in config.queries:
        payload = responses[query.query_id]
        hits = _response_hits(payload)
        for hit in hits:
            raw_url = hit.get("url")
            if not isinstance(raw_url, str) or not raw_url.strip():
                continue
            canonical_url = canonicalize_url(raw_url)
            reasons = _rejection_reasons(
                canonical_url,
                hit,
                allowed_domains=config.allowed_domains,
                require_pdf=config.require_pdf,
                required_url_terms=config.required_url_terms,
            )
            key = canonical_url or raw_url.strip()
            record = by_url.get(key)
            if record is None:
                record = {
                    "schema_version": 1,
                    "provider": "firecrawl-search",
                    "url": raw_url,
                    "canonical_url": canonical_url,
                    "query_ids": [],
                    "title": _optional_text(hit.get("title")),
                    "description": _optional_text(hit.get("description")),
                    "category": _optional_text(hit.get("category")),
                    "decision": "rejected" if reasons else "accepted",
                    "rejection_reasons": reasons,
                    "retrieved_at": timestamp,
                }
                by_url[key] = record
            record["query_ids"].append(query.query_id)

    records = sorted(
        by_url.values(), key=lambda row: row["canonical_url"] or row["url"]
    )
    for record in records:
        record["query_ids"] = sorted(set(record["query_ids"]))
    _write_jsonl(output_dir / "evidence.jsonl", records)
    accepted = sum(row["decision"] == "accepted" for row in records)
    summary: dict[str, int | bool] = {
        "valid": True,
        "accepted": accepted,
        "rejected": len(records) - accepted,
        "total": len(records),
    }
    _write_json(output_dir / "validation.json", summary)
    return summary


def _response_hits(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if payload.get("success") is not True:
        raise EvidenceSearchError("provider search failed")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise EvidenceSearchError("provider response data must be an object")
    web = data.get("web")
    if not isinstance(web, list):
        raise EvidenceSearchError("provider response data.web must be a list")
    if not all(isinstance(hit, Mapping) for hit in web):
        raise EvidenceSearchError("provider search hits must be objects")
    return web


def _rejection_reasons(
    canonical_url: str,
    hit: Mapping[str, Any],
    *,
    allowed_domains: tuple[str, ...],
    require_pdf: bool,
    required_url_terms: tuple[str, ...],
) -> list[str]:
    if not canonical_url:
        return ["invalid_url"]
    parsed = urlsplit(canonical_url)
    hostname = parsed.hostname or ""
    reasons = []
    if not any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in allowed_domains
    ):
        reasons.append("domain_not_allowed")
    category = _optional_text(hit.get("category")).lower()
    if require_pdf and not parsed.path.lower().endswith(".pdf") and category != "pdf":
        reasons.append("not_pdf")
    searchable_url = unquote(canonical_url).casefold()
    if not all(term in searchable_url for term in required_url_terms):
        reasons.append("url_terms_missing")
    return reasons


def _normalize_domain(value: Any) -> str:
    domain = _required_text(value, "allowed_domains[]").lower().strip(".")
    if "://" in domain or "/" in domain:
        raise EvidenceSearchError("allowed_domains must contain hostnames only")
    return domain


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceSearchError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _request_json(
    method: str,
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    request = Request(
        url,
        method=method,
        headers=dict(headers),
        data=json.dumps(payload).encode(),
    )
    try:
        with urlopen(request, timeout=120) as response:
            value = json.loads(response.read())
    except HTTPError as exc:
        detail = _provider_error(exc.read())
        suffix = f": {detail}" if detail else ""
        raise EvidenceSearchError(f"Firecrawl search HTTP {exc.code}{suffix}") from exc
    except Exception as exc:
        raise EvidenceSearchError(f"Firecrawl search request failed: {exc}") from exc
    if not isinstance(value, Mapping):
        raise EvidenceSearchError("provider response must be a JSON object")
    return value


def _provider_error(body: bytes) -> str:
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(value, Mapping) or not isinstance(value.get("error"), str):
        return ""
    return " ".join(value["error"].split())[:300]


def _search_request_contract(config: EvidenceSearchConfig) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "queries": [
            {"id": query.query_id, "query": query.text} for query in config.queries
        ],
        "limit": config.limit,
        "country": config.country,
        "require_pdf": config.require_pdf,
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _write_jsonl(path: Path, values: list[Mapping[str, Any]]) -> None:
    content = "".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values
    )
    _atomic_write(path, content)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)
