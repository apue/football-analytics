"""Provider-independent evidence bundle contract."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class EvidenceBundleError(ValueError):
    """Raised when an evidence bundle violates its versioned contract."""


_EVIDENCE_FIELDS = {
    "schema_version",
    "provider",
    "url",
    "canonical_url",
    "query_ids",
    "title",
    "description",
    "category",
    "decision",
    "rejection_reasons",
    "retrieved_at",
}


def canonicalize_url(value: str) -> str:
    """Return a stable HTTP(S) URL without fragments or tracking parameters."""

    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if scheme not in {"http", "https"} or not hostname:
        return ""
    port = parsed.port
    netloc = hostname
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        netloc = f"{hostname}:{port}"
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in {"fbclid", "gclid"}
        )
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def read_accepted_urls(path: Path) -> set[str]:
    """Read and validate canonical accepted URLs from an evidence bundle."""

    urls: set[str] = set()
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvidenceBundleError(
                f"invalid evidence JSON at line {line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise EvidenceBundleError(f"invalid evidence record at line {line_number}")
        if set(value) != _EVIDENCE_FIELDS:
            raise EvidenceBundleError(f"invalid evidence fields at line {line_number}")
        text_fields = (
            "provider",
            "url",
            "canonical_url",
            "title",
            "description",
            "category",
            "retrieved_at",
        )
        if any(not isinstance(value[field], str) for field in text_fields):
            raise EvidenceBundleError(f"invalid evidence text at line {line_number}")
        query_ids = value["query_ids"]
        reasons = value["rejection_reasons"]
        if (
            not isinstance(query_ids, list)
            or not all(isinstance(item, str) and item for item in query_ids)
            or len(query_ids) != len(set(query_ids))
            or not isinstance(reasons, list)
            or not all(isinstance(item, str) and item for item in reasons)
        ):
            raise EvidenceBundleError(f"invalid evidence lists at line {line_number}")
        decision = value["decision"]
        if decision not in {"accepted", "rejected"}:
            raise EvidenceBundleError(
                f"invalid evidence decision at line {line_number}"
            )
        canonical_url = value["canonical_url"]
        if canonical_url != canonicalize_url(value["url"]):
            raise EvidenceBundleError(f"invalid canonical URL at line {line_number}")
        if decision == "accepted":
            if not canonical_url or reasons:
                raise EvidenceBundleError(
                    f"invalid accepted evidence at line {line_number}"
                )
            url = canonical_url
            if url in urls:
                raise EvidenceBundleError(f"duplicate accepted URL: {url}")
            urls.add(url)
        elif not reasons:
            raise EvidenceBundleError(
                f"rejected evidence lacks reasons at line {line_number}"
            )
    return urls
