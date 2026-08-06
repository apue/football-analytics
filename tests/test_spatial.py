import json
from pathlib import Path

import pytest

from football_analytics.spatial import (
    MatchSpatialData,
    SpatialDataError,
    assert_spatial_quality,
    build_360_event_rows,
    build_spatial_quality_report,
    load_match_spatial_data,
    summarize_shot_direction,
)


def sample_event(
    event_id: str,
    *,
    index: int = 1,
    event_type: str = "Pass",
    team: str = "Barcelona",
    period: int = 1,
    location: list[float] | None = None,
) -> dict[str, object]:
    event: dict[str, object] = {
        "id": event_id,
        "index": index,
        "period": period,
        "minute": 1,
        "second": 2,
        "type": {"id": 30, "name": event_type},
        "team": {"id": 217, "name": team},
        "player": {"id": 5503, "name": "Sergio Busquets i Burgos"},
    }
    if location is not None:
        event["location"] = location
    if event_type == "Pass":
        event["pass"] = {"end_location": [60.0, 40.0]}
    return event


def sample_frame(event_id: str) -> dict[str, object]:
    return {
        "event_uuid": event_id,
        "freeze_frame": [
            {
                "teammate": True,
                "actor": True,
                "keeper": False,
                "location": [50.0, 40.0],
            },
            {
                "teammate": False,
                "actor": False,
                "keeper": True,
                "location": [110.0, 40.0],
            },
        ],
        "visible_area": [0.0, 0.0, 120.0, 0.0, 120.0, 80.0, 0.0, 80.0],
    }


def write_match(root: Path, match_id: int = 101) -> None:
    events_path = root / "data" / "events"
    frames_path = root / "data" / "three-sixty"
    events_path.mkdir(parents=True)
    frames_path.mkdir(parents=True)
    (events_path / f"{match_id}.json").write_text(
        json.dumps(
            [
                sample_event("event-1", location=[40.0, 30.0]),
                sample_event("event-2", index=2),
            ]
        )
    )
    (frames_path / f"{match_id}.json").write_text(json.dumps([sample_frame("event-1")]))


def test_load_report_and_join_preserve_structural_360_absence(tmp_path: Path) -> None:
    write_match(tmp_path)

    match = load_match_spatial_data(101, tmp_path)
    report = build_spatial_quality_report(match)
    assert_spatial_quality(report)
    rows = build_360_event_rows(match)

    assert report["event_count"] == 2
    assert report["frame_count"] == 1
    assert report["matched_frame_count"] == 1
    assert report["events_without_360_count"] == 1
    assert report["frame_coverage_rate"] == 0.5
    assert report["event_locations"] == {
        "count": 1,
        "malformed_count": 0,
        "outside_pitch_count": 0,
    }
    assert rows == [
        {
            "match_id": 101,
            "event_uuid": "event-1",
            "event_index": 1,
            "period": 1,
            "minute": 1,
            "second": 2,
            "event_type": "Pass",
            "team_id": 217,
            "team_name": "Barcelona",
            "player_id": 5503,
            "player_name": "Sergio Busquets i Burgos",
            "location": [40.0, 30.0],
            "freeze_frame": sample_frame("event-1")["freeze_frame"],
            "visible_area": sample_frame("event-1")["visible_area"],
            "visible_player_count": 2,
            "visible_teammate_count": 1,
            "visible_opponent_count": 1,
            "visible_actor_count": 1,
            "visible_keeper_count": 1,
        }
    ]


def test_report_distinguishes_nonfatal_invisible_actor() -> None:
    frame = sample_frame("event-1")
    for player in frame["freeze_frame"]:
        player["actor"] = False
    match = MatchSpatialData(
        101,
        (sample_event("event-1", location=[40.0, 30.0]),),
        (frame,),
    )

    report = build_spatial_quality_report(match)
    assert report["freeze_frames"]["without_visible_actor_count"] == 1
    assert_spatial_quality(report)


@pytest.mark.parametrize(
    ("events", "frames", "message"),
    [
        (
            [sample_event("event-1"), sample_event("event-1", index=2)],
            [sample_frame("event-1")],
            "duplicate_event_id_count",
        ),
        (
            [sample_event("event-1")],
            [sample_frame("unknown")],
            "unmatched 360 frames",
        ),
        (
            [sample_event("event-1", location=[121.0, 40.0])],
            [sample_frame("event-1")],
            "event_locations.outside_pitch_count",
        ),
    ],
)
def test_assert_spatial_quality_rejects_unsafe_data(
    events: list[dict[str, object]],
    frames: list[dict[str, object]],
    message: str,
) -> None:
    match = MatchSpatialData(101, tuple(events), tuple(frames))

    with pytest.raises(SpatialDataError, match=message):
        assert_spatial_quality(build_spatial_quality_report(match))


def test_join_rejects_duplicate_or_unmatched_identifiers() -> None:
    duplicate = MatchSpatialData(
        101,
        (sample_event("event-1"), sample_event("event-1", index=2)),
        (sample_frame("event-1"),),
    )
    unmatched = MatchSpatialData(
        101,
        (sample_event("event-1"),),
        (sample_frame("unknown"),),
    )

    with pytest.raises(SpatialDataError, match="duplicate event id"):
        build_360_event_rows(duplicate)
    with pytest.raises(SpatialDataError, match="do not match"):
        build_360_event_rows(unmatched)


def test_freeze_frame_player_outside_pitch_is_reported_but_allowed() -> None:
    frame = sample_frame("event-1")
    frame["freeze_frame"][0]["location"] = [-1.0, 40.0]
    match = MatchSpatialData(
        101,
        (sample_event("event-1", location=[40.0, 30.0]),),
        (frame,),
    )

    report = build_spatial_quality_report(match)

    assert report["freeze_frame_locations"]["outside_pitch_count"] == 1
    assert_spatial_quality(report)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("missing_visible_area", "visible_areas.missing_count"),
        ("multiple_actors", "freeze_frames.multiple_visible_actors_count"),
        ("missing_flag", "freeze_frames.malformed_player_flag_count"),
    ],
)
def test_assert_spatial_quality_rejects_unsafe_frame_structure(
    change: str, message: str
) -> None:
    frame = sample_frame("event-1")
    if change == "missing_visible_area":
        frame.pop("visible_area")
    elif change == "multiple_actors":
        frame["freeze_frame"][1]["actor"] = True
    else:
        frame["freeze_frame"][0].pop("keeper")
    match = MatchSpatialData(
        101,
        (sample_event("event-1", location=[40.0, 30.0]),),
        (frame,),
    )

    with pytest.raises(SpatialDataError, match=message):
        assert_spatial_quality(build_spatial_quality_report(match))


def test_shot_direction_is_grouped_by_team_and_period() -> None:
    events = [
        sample_event(
            "shot-1",
            event_type="Shot",
            team="Barcelona",
            period=1,
            location=[100.0, 40.0],
        ),
        sample_event(
            "shot-2",
            event_type="Shot",
            team="Barcelona",
            period=2,
            location=[90.0, 35.0],
        ),
        sample_event(
            "shot-3",
            event_type="Shot",
            team="Real Madrid",
            period=2,
            location=[110.0, 42.0],
        ),
    ]

    rows = summarize_shot_direction(events)

    assert [(row["team_name"], row["period"]) for row in rows] == [
        ("Barcelona", 1),
        ("Barcelona", 2),
        ("Real Madrid", 2),
    ]
    assert all(row["attacking_half_count"] == row["shot_count"] for row in rows)


def test_loader_reports_missing_or_invalid_sources(tmp_path: Path) -> None:
    with pytest.raises(SpatialDataError, match="positive integer"):
        load_match_spatial_data(0, tmp_path)
    with pytest.raises(SpatialDataError, match="does not exist"):
        load_match_spatial_data(101, tmp_path)

    events = tmp_path / "data" / "events"
    frames = tmp_path / "data" / "three-sixty"
    events.mkdir(parents=True)
    frames.mkdir(parents=True)
    (events / "101.json").write_text("{}")
    (frames / "101.json").write_text("[]")
    with pytest.raises(SpatialDataError, match="list of objects"):
        load_match_spatial_data(101, tmp_path)
