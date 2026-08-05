"""Reusable loading and validation for StatsBomb event and 360 spatial data.

StatsBomb event and 360 coordinates use a 120 by 80 pitch coordinate system.
Event locations are already represented with the team in possession attacking
from left to right, so callers must not flip second-half coordinates again.
Freeze-frame player locations can fall outside the pitch lines and therefore
need to be reported separately rather than filtered by the event rule.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from football_analytics.paths import get_open_data_root

PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0


class SpatialDataError(ValueError):
    """Raised when spatial source files cannot produce an unambiguous table."""


@dataclass(frozen=True)
class MatchSpatialData:
    """Raw event and 360 records for one match.

    Attributes:
        match_id: Stable StatsBomb match identifier.
        events: Event JSON records in provider order.
        frames: 360 frame JSON records. A frame is not expected for every event.
    """

    match_id: int
    events: tuple[Mapping[str, Any], ...]
    frames: tuple[Mapping[str, Any], ...]


def load_match_spatial_data(
    match_id: int, open_data_root: Path | None = None
) -> MatchSpatialData:
    """Load one match's StatsBomb events and 360 frames.

    Args:
        match_id: Stable StatsBomb match ID.
        open_data_root: Root of the StatsBomb open-data checkout. When omitted,
            the repository default or ``STATSBOMB_OPEN_DATA`` override is used.

    Returns:
        A :class:`MatchSpatialData` container. Records are not filtered and 360
        absence is preserved because it is structural rather than automatically
        a data error.

    Raises:
        SpatialDataError: If ``match_id`` is invalid, either source file is
            missing, malformed JSON, or does not contain a JSON list.

    Coordinate contract:
        Locations use the provider's 120 x 80, possession-team-relative frame:
        the team in possession attacks towards x=120. Do not flip by period.
    """
    if isinstance(match_id, bool) or not isinstance(match_id, int) or match_id <= 0:
        raise SpatialDataError("match_id must be a positive integer")

    root = (open_data_root or get_open_data_root()).resolve()
    events = _load_json_list(root / "data" / "events" / f"{match_id}.json")
    frames = _load_json_list(root / "data" / "three-sixty" / f"{match_id}.json")
    return MatchSpatialData(match_id, tuple(events), tuple(frames))


def build_360_event_rows(match: MatchSpatialData) -> list[dict[str, Any]]:
    """Join every 360 frame to its event and return concatenation-safe rows.

    Args:
        match: Records returned by :func:`load_match_spatial_data`.

    Returns:
        One dictionary per 360 frame. Each row retains ``match_id`` and
        ``event_uuid`` plus event context, raw ``freeze_frame`` and
        ``visible_area`` values, and visible-player counts. Rows from different
        matches can therefore be concatenated without losing provenance.

    Raises:
        SpatialDataError: If event IDs or frame UUIDs are missing or duplicated,
            or a frame cannot be joined to an event. Run
            :func:`build_spatial_quality_report` first to diagnose the problem.
    """
    event_index = _unique_index(match.events, "id", "event")
    frame_index = _unique_index(match.frames, "event_uuid", "360 frame")
    unmatched = sorted(set(frame_index) - set(event_index))
    if unmatched:
        raise SpatialDataError(
            f"{len(unmatched)} 360 frame UUIDs do not match an event"
        )

    rows: list[dict[str, Any]] = []
    for frame in match.frames:
        event_uuid = frame["event_uuid"]
        event = event_index[event_uuid]
        players = frame.get("freeze_frame")
        players = players if isinstance(players, list) else []
        team = event.get("team") if isinstance(event.get("team"), dict) else {}
        player = event.get("player") if isinstance(event.get("player"), dict) else {}
        event_type = event.get("type") if isinstance(event.get("type"), dict) else {}
        rows.append(
            {
                "match_id": match.match_id,
                "event_uuid": event_uuid,
                "event_index": event.get("index"),
                "period": event.get("period"),
                "minute": event.get("minute"),
                "second": event.get("second"),
                "event_type": event_type.get("name"),
                "team_id": team.get("id"),
                "team_name": team.get("name"),
                "player_id": player.get("id"),
                "player_name": player.get("name"),
                "location": event.get("location"),
                "freeze_frame": frame.get("freeze_frame"),
                "visible_area": frame.get("visible_area"),
                "visible_player_count": len(players),
                "visible_teammate_count": sum(
                    item.get("teammate") is True
                    for item in players
                    if isinstance(item, dict)
                ),
                "visible_opponent_count": sum(
                    item.get("teammate") is False
                    for item in players
                    if isinstance(item, dict)
                ),
                "visible_actor_count": sum(
                    item.get("actor") is True
                    for item in players
                    if isinstance(item, dict)
                ),
                "visible_keeper_count": sum(
                    item.get("keeper") is True
                    for item in players
                    if isinstance(item, dict)
                ),
            }
        )
    return rows


def build_spatial_quality_report(match: MatchSpatialData) -> dict[str, Any]:
    """Calculate deterministic event–360 association and coordinate checks.

    Args:
        match: One match's unfiltered event and 360 records.

    Returns:
        A nested dictionary of counts. Coordinate sections distinguish malformed
        values from numeric values outside the inclusive 120 x 80 pitch lines.
        ``events_without_360_count``, frames without a visible actor, and
        freeze-frame players outside the pitch are reported but are not
        automatically failures.
    """
    event_ids = [event.get("id") for event in match.events]
    frame_ids = [frame.get("event_uuid") for frame in match.frames]
    valid_event_ids = {value for value in event_ids if _valid_id(value)}
    valid_frame_ids = {value for value in frame_ids if _valid_id(value)}

    event_locations = [
        event.get("location") for event in match.events if "location" in event
    ]
    end_locations = list(_event_end_locations(match.events))
    freeze_locations: list[Any] = []
    empty_freeze_frames = 0
    frames_without_actor = 0
    frames_with_multiple_actors = 0
    malformed_freeze_frames = 0
    malformed_freeze_players = 0
    malformed_player_flags = 0
    for frame in match.frames:
        players = frame.get("freeze_frame")
        if not isinstance(players, list):
            malformed_freeze_frames += 1
            continue
        if not players:
            empty_freeze_frames += 1
        actors = 0
        for item in players:
            if isinstance(item, dict):
                freeze_locations.append(item.get("location"))
                actors += item.get("actor") is True
                malformed_player_flags += any(
                    not isinstance(item.get(flag), bool)
                    for flag in ("teammate", "actor", "keeper")
                )
            else:
                malformed_freeze_players += 1
                freeze_locations.append(None)
        frames_without_actor += actors == 0
        frames_with_multiple_actors += actors > 1

    visible_areas: list[Any] = []
    missing_visible_areas = 0
    malformed_visible_areas = 0
    for frame in match.frames:
        area = frame.get("visible_area")
        if area is None:
            missing_visible_areas += 1
            continue
        if not _flat_numeric_pairs(area):
            malformed_visible_areas += 1
            continue
        visible_areas.extend(
            [[area[index], area[index + 1]] for index in range(0, len(area), 2)]
        )

    matched_ids = valid_event_ids & valid_frame_ids
    return {
        "match_id": match.match_id,
        "event_count": len(match.events),
        "frame_count": len(match.frames),
        "matched_frame_count": len(matched_ids),
        "unmatched_frame_count": len(valid_frame_ids - valid_event_ids),
        "events_without_360_count": len(valid_event_ids - valid_frame_ids),
        "frame_coverage_rate": (
            len(matched_ids) / len(valid_event_ids) if valid_event_ids else 0.0
        ),
        "identifiers": {
            "missing_event_id_count": sum(not _valid_id(value) for value in event_ids),
            "duplicate_event_id_count": _duplicate_count(event_ids),
            "missing_frame_uuid_count": sum(
                not _valid_id(value) for value in frame_ids
            ),
            "duplicate_frame_uuid_count": _duplicate_count(frame_ids),
        },
        "event_locations": _coordinate_report(event_locations),
        "event_end_locations": _coordinate_report(end_locations),
        "freeze_frame_locations": _coordinate_report(freeze_locations),
        "visible_area_vertices": _coordinate_report(visible_areas),
        "freeze_frames": {
            "malformed_count": malformed_freeze_frames,
            "malformed_player_count": malformed_freeze_players,
            "malformed_player_flag_count": malformed_player_flags,
            "empty_count": empty_freeze_frames,
            "without_visible_actor_count": frames_without_actor,
            "multiple_visible_actors_count": frames_with_multiple_actors,
        },
        "visible_areas": {
            "missing_count": missing_visible_areas,
            "malformed_count": malformed_visible_areas,
        },
    }


def assert_spatial_quality(report: Mapping[str, Any]) -> None:
    """Raise when a quality report contains an unsafe association or coordinate.

    Structural absence is intentionally allowed: not every event has a 360
    frame, the actor can be outside a frame's visible area, and freeze-frame
    players can be positioned outside the pitch lines. These counts must still
    be interpreted by the analyst.

    Args:
        report: Output from :func:`build_spatial_quality_report`.

    Raises:
        SpatialDataError: If identifiers are missing/duplicated, a frame is
            unmatched, spatial values are malformed/out of bounds, or frame and
            visible-area containers are malformed.
    """
    failures: list[str] = []
    if report.get("unmatched_frame_count"):
        failures.append("unmatched 360 frames")

    identifiers = report.get("identifiers", {})
    for key in (
        "missing_event_id_count",
        "duplicate_event_id_count",
        "missing_frame_uuid_count",
        "duplicate_frame_uuid_count",
    ):
        if identifiers.get(key):
            failures.append(key)

    for section_name in (
        "event_locations",
        "event_end_locations",
        "freeze_frame_locations",
        "visible_area_vertices",
    ):
        section = report.get(section_name, {})
        if section.get("malformed_count"):
            failures.append(f"{section_name}.malformed_count")
        if section_name != "freeze_frame_locations" and section.get(
            "outside_pitch_count"
        ):
            failures.append(f"{section_name}.outside_pitch_count")

    freeze_frames = report.get("freeze_frames", {})
    for key in (
        "malformed_count",
        "malformed_player_count",
        "malformed_player_flag_count",
        "empty_count",
        "multiple_visible_actors_count",
    ):
        if freeze_frames.get(key):
            failures.append(f"freeze_frames.{key}")

    visible_areas = report.get("visible_areas", {})
    for key in ("malformed_count", "missing_count"):
        if visible_areas.get(key):
            failures.append(f"visible_areas.{key}")

    if failures:
        raise SpatialDataError("Spatial quality checks failed: " + ", ".join(failures))


def summarize_shot_direction(
    events: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Summarize shot x-locations by team and period as a direction sanity check.

    StatsBomb presents each possession team as attacking towards x=120. A table
    split by team and period makes that convention inspectable without applying
    an additional half-time flip. This is a sanity check, not proof that every
    shot must be close to goal.

    Args:
        events: StatsBomb event mappings.

    Returns:
        Sorted dictionaries with team, period, shot count, median start x and
        the count of shots whose start x is in the attacking half (x >= 60).
    """
    groups: dict[tuple[int | None, str | None, int | None], list[float]] = {}
    for event in events:
        event_type = event.get("type")
        if not isinstance(event_type, dict) or event_type.get("name") != "Shot":
            continue
        location = event.get("location")
        if not _valid_coordinate(location):
            continue
        team = event.get("team") if isinstance(event.get("team"), dict) else {}
        key = (team.get("id"), team.get("name"), event.get("period"))
        groups.setdefault(key, []).append(float(location[0]))

    return [
        {
            "team_id": team_id,
            "team_name": team_name,
            "period": period,
            "shot_count": len(values),
            "median_start_x": median(values),
            "attacking_half_count": sum(value >= PITCH_LENGTH / 2 for value in values),
        }
        for (team_id, team_name, period), values in sorted(
            groups.items(), key=lambda item: (str(item[0][1]), item[0][2] or 0)
        )
    ]


def _load_json_list(path: Path) -> list[Mapping[str, Any]]:
    if not path.is_file():
        raise SpatialDataError(f"Required spatial data file does not exist: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SpatialDataError(
            f"Could not read spatial data file {path}: {error}"
        ) from error
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise SpatialDataError(
            f"Spatial data file must contain a list of objects: {path}"
        )
    return value


def _unique_index(
    records: Iterable[Mapping[str, Any]], key: str, label: str
) -> dict[str, Mapping[str, Any]]:
    records = list(records)
    values = [record.get(key) for record in records]
    if any(not _valid_id(value) for value in values):
        raise SpatialDataError(f"Every {label} must have a non-empty {key}")
    duplicates = _duplicate_count(values)
    if duplicates:
        raise SpatialDataError(f"{duplicates} duplicate {label} {key} values")
    return {value: record for value, record in zip(values, records, strict=True)}


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _duplicate_count(values: Sequence[Any]) -> int:
    valid_values = [value for value in values if _valid_id(value)]
    return sum(count - 1 for count in Counter(valid_values).values() if count > 1)


def _event_end_locations(events: Iterable[Mapping[str, Any]]) -> Iterable[Any]:
    for event in events:
        for value in event.values():
            if isinstance(value, dict) and "end_location" in value:
                yield value["end_location"]


def _coordinate_report(values: Sequence[Any]) -> dict[str, int]:
    malformed_count = sum(not _valid_coordinate(value) for value in values)
    outside_pitch_count = sum(
        _valid_coordinate(value) and not _inside_pitch(value) for value in values
    )
    return {
        "count": len(values),
        "malformed_count": malformed_count,
        "outside_pitch_count": outside_pitch_count,
    }


def _valid_coordinate(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= 2
        and all(
            isinstance(coordinate, (int, float))
            and not isinstance(coordinate, bool)
            and math.isfinite(coordinate)
            for coordinate in value[:2]
        )
    )


def _inside_pitch(value: Sequence[float]) -> bool:
    return 0 <= value[0] <= PITCH_LENGTH and 0 <= value[1] <= PITCH_WIDTH


def _flat_numeric_pairs(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= 6
        and len(value) % 2 == 0
        and all(
            isinstance(coordinate, (int, float))
            and not isinstance(coordinate, bool)
            and math.isfinite(coordinate)
            for coordinate in value
        )
    )
