"""Reusable tools for the football analytics learning project."""

from football_analytics.evidence import build_match_evidence
from football_analytics.paths import (
    get_book_reference_root,
    get_catalog_path,
    get_open_data_root,
    get_project_root,
)

__all__ = [
    "build_match_evidence",
    "get_book_reference_root",
    "get_catalog_path",
    "get_open_data_root",
    "get_project_root",
]
