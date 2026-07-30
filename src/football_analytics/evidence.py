"""Reusable evidence extraction from one StatsBomb event file."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


class EvidenceError(ValueError):
    """Raised when event data cannot satisfy the match-evidence interface."""


def build_match_evidence(
    events: Sequence[Mapping[str, Any]],
    *,
    final_third_x: float = 80.0,
) -> dict[str, Any]:
    """Build a JSON-serializable evidence packet for one StatsBomb match.

    The packet contains successful Pass/Carry entries into the final third,
    possession outcomes after the first entry, provider-labelled counter
    possessions, and auditable goal context. It reports recorded events and
    deterministic metrics; it does not infer tactical causes.
    """

    if not events:
        raise EvidenceError("events must contain one match")
    if not 0 < final_third_x < 120:
        raise EvidenceError("final_third_x must be inside the StatsBomb pitch")

    ordered = sorted(events, key=lambda event: event["index"])
    teams = list(
        dict.fromkeys(
            event["team"]["name"]
            for event in ordered
            if event.get("team", {}).get("name")
        )
    )
    if len(teams) != 2:
        raise EvidenceError(f"expected two teams, found {len(teams)}")

    entries = _extract_entries(ordered, final_third_x)
    entry_possessions = _entry_possession_outcomes(ordered, entries, teams)
    goals = _extract_goals(ordered)
    counter_possessions = _extract_counter_possessions(ordered)

    return {
        "schema_version": 1,
        "match": {
            "event_count": len(ordered),
            "teams": teams,
            "event_type_count": len({event["type"]["name"] for event in ordered}),
            "shot_goal_count": len(goals),
        },
        "definitions": {
            "final_third_entry": (
                f"successful Pass or Carry with start_x < {final_third_x:g} <= end_x"
            ),
            "entry_possession": (
                "first successful final-third entry in each StatsBomb possession"
            ),
            "counter": 'StatsBomb play_pattern == "From Counter"',
            "evidence_boundary": (
                "recorded on-ball events and linked provider labels; "
                "no tactical-cause inference"
            ),
        },
        "final_third_entries": entries,
        "entry_possessions": entry_possessions,
        "entry_summary": _entry_summary(entry_possessions, teams),
        "counter_possessions": counter_possessions,
        "goals": goals,
    }


def _extract_entries(
    events: Sequence[Mapping[str, Any]],
    final_third_x: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        method = event["type"]["name"]
        start = event.get("location")
        if method not in {"Pass", "Carry"} or start is None:
            continue

        detail = event[method.lower()]
        end = detail.get("end_location")
        if end is None or not start[0] < final_third_x <= end[0]:
            continue
        if method == "Pass" and detail.get("outcome") is not None:
            continue

        rows.append(
            {
                "event_id": event["id"],
                "event_index": event["index"],
                "possession": event["possession"],
                "minute": event["minute"],
                "team": event["team"]["name"],
                "player": event.get("player", {}).get("name"),
                "method": method,
                "play_pattern": event["play_pattern"]["name"],
                "pass_type": (
                    detail.get("type", {}).get("name") if method == "Pass" else None
                ),
                "pass_height": (
                    detail.get("height", {}).get("name") if method == "Pass" else None
                ),
                "length": detail.get("length", math.dist(start, end)),
                "start_x": start[0],
                "start_y": start[1],
                "end_x": end[0],
                "end_y": end[1],
            }
        )
    return rows


def _entry_possession_outcomes(
    events: Sequence[Mapping[str, Any]],
    entries: Sequence[Mapping[str, Any]],
    teams: Sequence[str],
) -> list[dict[str, Any]]:
    events_by_possession: dict[int, list[Mapping[str, Any]]] = {}
    score_before_event: dict[int, dict[str, int]] = {}
    score = dict.fromkeys(teams, 0)

    for event in events:
        events_by_possession.setdefault(event["possession"], []).append(event)
        score_before_event[event["index"]] = score.copy()
        if _is_shot_goal(event):
            score[event["team"]["name"]] += 1

    first_entries: dict[int, Mapping[str, Any]] = {}
    for entry in sorted(entries, key=lambda row: row["event_index"]):
        first_entries.setdefault(entry["possession"], entry)

    rows: list[dict[str, Any]] = []
    for entry in first_entries.values():
        possession_events = events_by_possession[entry["possession"]]
        attacking_events = [
            event
            for event in possession_events
            if event["index"] >= entry["event_index"]
            and event.get("team", {}).get("name") == entry["team"]
        ]
        shots = [event for event in attacking_events if event["type"]["name"] == "Shot"]
        opponent = next(team for team in teams if team != entry["team"])
        score_at_entry = score_before_event[entry["event_index"]]
        score_state = (
            "Level"
            if score_at_entry[entry["team"]] == score_at_entry[opponent]
            else "Leading"
            if score_at_entry[entry["team"]] > score_at_entry[opponent]
            else "Trailing"
        )
        rows.append(
            {
                "possession": entry["possession"],
                "team": entry["team"],
                "entry_minute": entry["minute"],
                "entry_player": entry["player"],
                "entry_method": entry["method"],
                "entry_height": entry["pass_height"],
                "play_pattern": entry["play_pattern"],
                "score_state": score_state,
                "reached_box": any(
                    _event_reaches_box(event) for event in attacking_events
                ),
                "has_shot": bool(shots),
                "xg": sum(
                    shot.get("shot", {}).get("statsbomb_xg", 0.0) for shot in shots
                ),
                "goal": any(_is_shot_goal(shot) for shot in shots),
            }
        )
    return rows


def _inside_box(location: Sequence[float] | None) -> bool:
    return bool(location and location[0] >= 102 and 18 <= location[1] <= 62)


def _event_reaches_box(event: Mapping[str, Any]) -> bool:
    if _inside_box(event.get("location")):
        return True
    event_type = event["type"]["name"]
    if event_type not in {"Pass", "Carry"}:
        return False
    detail = event[event_type.lower()]
    if event_type == "Pass" and detail.get("outcome") is not None:
        return False
    return _inside_box(detail.get("end_location"))


def _entry_summary(
    outcomes: Sequence[Mapping[str, Any]],
    teams: Sequence[str],
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for team in teams:
        team_rows = [row for row in outcomes if row["team"] == team]
        count = len(team_rows)
        reached_box = sum(bool(row["reached_box"]) for row in team_rows)
        shots = sum(bool(row["has_shot"]) for row in team_rows)
        xg = sum(float(row["xg"]) for row in team_rows)
        goals = sum(bool(row["goal"]) for row in team_rows)
        summary[team] = {
            "entry_possessions": count,
            "reached_box": reached_box,
            "shot_possessions": shots,
            "xg": xg,
            "goals": goals,
            "box_reach_rate": reached_box / count if count else 0.0,
            "shot_rate": shots / count if count else 0.0,
            "xg_per_entry_possession": xg / count if count else 0.0,
        }
    return summary


def _extract_counter_possessions(
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for event in events:
        if event["play_pattern"]["name"] == "From Counter":
            grouped.setdefault(event["possession"], []).append(event)

    rows: list[dict[str, Any]] = []
    for possession, possession_events in grouped.items():
        possession_team = possession_events[0]["possession_team"]["name"]
        shots = [
            event
            for event in possession_events
            if event.get("team", {}).get("name") == possession_team
            and event["type"]["name"] == "Shot"
        ]
        rows.append(
            {
                "possession": possession,
                "team": possession_team,
                "start_minute": min(event["minute"] for event in possession_events),
                "event_count": len(possession_events),
                "has_shot": bool(shots),
                "xg": sum(
                    shot.get("shot", {}).get("statsbomb_xg", 0.0) for shot in shots
                ),
                "goal": any(_is_shot_goal(shot) for shot in shots),
            }
        )
    return rows


def _extract_goals(
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {event["id"]: event for event in events}
    by_possession: dict[int, list[Mapping[str, Any]]] = {}
    for event in events:
        by_possession.setdefault(event["possession"], []).append(event)

    rows: list[dict[str, Any]] = []
    for event in events:
        if not _is_shot_goal(event):
            continue
        shot = event["shot"]
        possession_events = by_possession[event["possession"]]
        key_pass = by_id.get(shot.get("key_pass_id"))
        penalty_award = (
            _find_penalty_award(events, by_id, event)
            if shot["type"]["name"] == "Penalty"
            else None
        )
        recoveries = [
            candidate
            for candidate in possession_events
            if candidate["index"] < event["index"]
            and candidate.get("team", {}).get("name") == event["team"]["name"]
            and candidate["type"]["name"] == "Ball Recovery"
        ]
        start = possession_events[0]
        rows.append(
            {
                "event_id": event["id"],
                "event_index": event["index"],
                "minute": event["minute"],
                "second": event["second"],
                "period": event["period"],
                "team": event["team"]["name"],
                "player": event["player"]["name"],
                "possession": event["possession"],
                "play_pattern": event["play_pattern"]["name"],
                "shot_type": shot["type"]["name"],
                "shot_xg": shot["statsbomb_xg"],
                "shot_technique": shot["technique"]["name"],
                "shot_body_part": shot["body_part"]["name"],
                "one_on_one": bool(shot.get("one_on_one")),
                "first_time": bool(shot.get("first_time")),
                "location": event.get("location"),
                "end_location": shot.get("end_location"),
                "key_pass": _pass_evidence(key_pass) if key_pass else None,
                "penalty_award": penalty_award,
                "last_ball_recovery": (
                    _basic_event(recoveries[-1]) if recoveries else None
                ),
                "possession_start": _basic_event(start),
                "possession_event_count": len(possession_events),
                "seconds_from_possession_start": (
                    event["minute"] * 60
                    + event["second"]
                    - start["minute"] * 60
                    - start["second"]
                ),
            }
        )
    return rows


def _find_penalty_award(
    events: Sequence[Mapping[str, Any]],
    by_id: Mapping[str, Mapping[str, Any]],
    penalty_shot: Mapping[str, Any],
) -> dict[str, Any] | None:
    for event in reversed(events):
        if event["index"] >= penalty_shot["index"]:
            continue
        if event["period"] != penalty_shot["period"]:
            break
        if (
            event["type"]["name"] == "Foul Won"
            and event.get("team", {}).get("name") == penalty_shot["team"]["name"]
            and event.get("foul_won", {}).get("penalty") is True
        ):
            committed = next(
                (
                    by_id[event_id]
                    for event_id in event.get("related_events", [])
                    if by_id.get(event_id, {}).get("type", {}).get("name")
                    == "Foul Committed"
                ),
                None,
            )
            return {
                "foul_won": _basic_event(event),
                "foul_committed": (
                    _basic_event(committed) if committed is not None else None
                ),
            }
    return None


def _pass_evidence(event: Mapping[str, Any]) -> dict[str, Any]:
    detail = event["pass"]
    return {
        **_basic_event(event),
        "recipient": detail.get("recipient", {}).get("name"),
        "end_location": detail.get("end_location"),
        "height": detail.get("height", {}).get("name"),
        "type": detail.get("type", {}).get("name"),
        "technique": detail.get("technique", {}).get("name"),
        "through_ball": bool(detail.get("through_ball")),
        "cross": bool(detail.get("cross")),
        "cut_back": bool(detail.get("cut_back")),
        "goal_assist": bool(detail.get("goal_assist")),
    }


def _basic_event(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event["id"],
        "event_index": event["index"],
        "minute": event["minute"],
        "second": event["second"],
        "team": event["team"]["name"],
        "player": event.get("player", {}).get("name"),
        "type": event["type"]["name"],
        "location": event.get("location"),
        "play_pattern": event["play_pattern"]["name"],
    }


def _is_shot_goal(event: Mapping[str, Any]) -> bool:
    return (
        event["type"]["name"] == "Shot"
        and event.get("shot", {}).get("outcome", {}).get("name") == "Goal"
    )
