import json
from pathlib import Path

from football_analytics.evidence import build_match_evidence
from football_analytics.evidence_cli import main


def event(
    index: int,
    *,
    event_id: str,
    team: str,
    event_type: str,
    possession: int,
    pattern: str = "Regular Play",
    location: list[float] | None = None,
    player: str | None = None,
    detail: dict[str, object] | None = None,
    related_events: list[str] | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": event_id,
        "index": index,
        "period": 1,
        "timestamp": f"00:00:{index:02}.000",
        "minute": 0,
        "second": index,
        "type": {"name": event_type},
        "possession": possession,
        "possession_team": {"name": team},
        "play_pattern": {"name": pattern},
        "team": {"name": team},
    }
    if location is not None:
        row["location"] = location
    if player is not None:
        row["player"] = {"name": player}
    if detail is not None:
        row[event_type.lower().replace(" ", "_").replace("*", "")] = detail
    if related_events is not None:
        row["related_events"] = related_events
    return row


def match_events() -> list[dict[str, object]]:
    rows = [
        event(
            1,
            event_id="start-a",
            team="Alpha",
            event_type="Starting XI",
            possession=1,
        ),
        event(
            2,
            event_id="start-b",
            team="Beta",
            event_type="Starting XI",
            possession=1,
        ),
        event(
            3,
            event_id="assist",
            team="Alpha",
            player="Creator",
            event_type="Pass",
            possession=2,
            location=[70.0, 40.0],
            detail={
                "recipient": {"name": "Scorer"},
                "end_location": [105.0, 40.0],
                "height": {"name": "Ground Pass"},
                "technique": {"name": "Through Ball"},
                "through_ball": True,
                "goal_assist": True,
            },
        ),
        event(
            4,
            event_id="goal-a",
            team="Alpha",
            player="Scorer",
            event_type="Shot",
            possession=2,
            location=[105.0, 40.0],
            detail={
                "statsbomb_xg": 0.4,
                "end_location": [120.0, 40.0, 1.0],
                "key_pass_id": "assist",
                "type": {"name": "Open Play"},
                "outcome": {"name": "Goal"},
                "technique": {"name": "Normal"},
                "body_part": {"name": "Right Foot"},
                "one_on_one": True,
            },
        ),
        event(
            5,
            event_id="carry-entry",
            team="Beta",
            player="Runner",
            event_type="Carry",
            possession=3,
            pattern="From Counter",
            location=[75.0, 30.0],
            detail={"end_location": [85.0, 30.0]},
        ),
        event(
            6,
            event_id="saved-shot",
            team="Beta",
            player="Shooter",
            event_type="Shot",
            possession=3,
            pattern="From Counter",
            location=[100.0, 30.0],
            detail={
                "statsbomb_xg": 0.1,
                "end_location": [120.0, 40.0, 1.0],
                "type": {"name": "Open Play"},
                "outcome": {"name": "Saved"},
                "technique": {"name": "Normal"},
                "body_part": {"name": "Right Foot"},
            },
        ),
        event(
            7,
            event_id="failed-entry",
            team="Alpha",
            event_type="Pass",
            possession=4,
            location=[70.0, 50.0],
            detail={
                "end_location": [90.0, 50.0],
                "height": {"name": "High Pass"},
                "outcome": {"name": "Incomplete"},
            },
        ),
        event(
            8,
            event_id="foul-committed",
            team="Beta",
            player="Defender",
            event_type="Foul Committed",
            possession=5,
            location=[10.0, 40.0],
            detail={"penalty": True},
            related_events=["foul-won"],
        ),
        event(
            9,
            event_id="foul-won",
            team="Alpha",
            player="Scorer",
            event_type="Foul Won",
            possession=5,
            location=[110.0, 40.0],
            detail={"penalty": True},
            related_events=["foul-committed"],
        ),
        event(
            10,
            event_id="penalty-goal",
            team="Alpha",
            player="Scorer",
            event_type="Shot",
            possession=6,
            pattern="Other",
            location=[108.0, 40.0],
            detail={
                "statsbomb_xg": 0.78,
                "end_location": [120.0, 40.0, 1.0],
                "type": {"name": "Penalty"},
                "outcome": {"name": "Goal"},
                "technique": {"name": "Normal"},
                "body_part": {"name": "Right Foot"},
            },
        ),
    ]
    for row in rows:
        if row["id"] in {"start-b", "carry-entry", "saved-shot", "foul-committed"}:
            row["possession_team"] = {"name": "Beta"}
        else:
            row["possession_team"] = {"name": "Alpha"}
    return rows


def test_match_evidence_extracts_entries_outcomes_and_provider_counters() -> None:
    evidence = build_match_evidence(match_events())

    assert [row["event_id"] for row in evidence["final_third_entries"]] == [
        "assist",
        "carry-entry",
    ]
    assert evidence["entry_summary"]["Alpha"] == {
        "entry_possessions": 1,
        "reached_box": 1,
        "shot_possessions": 1,
        "xg": 0.4,
        "goals": 1,
        "box_reach_rate": 1.0,
        "shot_rate": 1.0,
        "xg_per_entry_possession": 0.4,
    }
    assert evidence["entry_summary"]["Beta"]["shot_rate"] == 1.0
    assert evidence["entry_possessions"][1]["score_state"] == "Trailing"
    assert evidence["counter_possessions"] == [
        {
            "possession": 3,
            "team": "Beta",
            "start_minute": 0,
            "event_count": 2,
            "has_shot": True,
            "xg": 0.1,
            "goal": False,
        }
    ]


def test_match_evidence_links_assists_and_penalty_fouls() -> None:
    evidence = build_match_evidence(match_events())
    open_play, penalty = evidence["goals"]

    assert open_play["key_pass"]["player"] == "Creator"
    assert open_play["key_pass"]["through_ball"] is True
    assert open_play["one_on_one"] is True
    assert penalty["key_pass"] is None
    assert penalty["penalty_award"]["foul_won"]["player"] == "Scorer"
    assert penalty["penalty_award"]["foul_committed"]["player"] == "Defender"


def test_match_evidence_cli_emits_markdown(
    tmp_path: Path,
    capsys: object,
) -> None:
    source_root = tmp_path / "open-data"
    events_path = source_root / "data" / "events" / "99.json"
    events_path.parent.mkdir(parents=True)
    events_path.write_text(json.dumps(match_events()))

    result = main(
        [
            "--match-id",
            "99",
            "--open-data-root",
            str(source_root),
            "--format",
            "markdown",
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert "# Match evidence: 99" in output
    assert "| Alpha | 1 | 1 | 1 | 0.400 | 1 |" in output
    assert "| 1 | Alpha | Scorer | Regular Play | 0.400 | Creator | — |" in output
