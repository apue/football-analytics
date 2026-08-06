"""Reusable tools for the football analytics learning project."""

from football_analytics.evidence import build_match_evidence
from football_analytics.paths import (
    get_book_reference_root,
    get_catalog_path,
    get_open_data_root,
    get_project_root,
)
from football_analytics.spatial import (
    MatchSpatialData,
    SpatialDataError,
    assert_spatial_quality,
    build_360_event_rows,
    build_spatial_quality_report,
    load_match_spatial_data,
    summarize_shot_direction,
)

__all__ = [
    "build_match_evidence",
    "get_book_reference_root",
    "get_catalog_path",
    "get_open_data_root",
    "get_project_root",
    "MatchSpatialData",
    "SpatialDataError",
    "assert_spatial_quality",
    "build_360_event_rows",
    "build_spatial_quality_report",
    "load_match_spatial_data",
    "summarize_shot_direction",
]
