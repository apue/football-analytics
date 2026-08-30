"""Provider-independent evidence bundle contract."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class EvidenceBundleError(ValueError):
    """Raised when an evidence bundle violates its versioned contract."""


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
        if value.get("decision") == "accepted":
            url = value.get("canonical_url")
            if not isinstance(url, str) or not url:
                raise EvidenceBundleError(
                    f"accepted evidence lacks canonical_url at line {line_number}"
                )
            if url in urls:
                raise EvidenceBundleError(f"duplicate accepted URL: {url}")
            urls.add(url)
    return urls
