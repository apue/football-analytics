"""Command-line interface for a reusable StatsBomb match evidence packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from football_analytics.evidence import EvidenceError, build_match_evidence
from football_analytics.paths import get_open_data_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="match-evidence",
        description="Extract reusable evidence from one local StatsBomb event file.",
    )
    parser.add_argument("--match-id", type=int, required=True)
    parser.add_argument("--open-data-root", type=Path, default=None)
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    return parser


def _render_markdown(match_id: int, evidence: dict[str, Any]) -> str:
    lines = [
        f"# Match evidence: {match_id}",
        "",
        f"- Events: {evidence['match']['event_count']}",
        f"- Teams: {', '.join(evidence['match']['teams'])}",
        f"- Final-third entries: {len(evidence['final_third_entries'])}",
        f"- Entry possessions: {len(evidence['entry_possessions'])}",
        f"- From Counter possessions: {len(evidence['counter_possessions'])}",
        f"- Shot goals: {len(evidence['goals'])}",
        "",
        "## Entry outcomes",
        "",
        "| Team | Entries | Reached box | Shots | xG | Goals |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for team, row in evidence["entry_summary"].items():
        lines.append(
            f"| {team} | {row['entry_possessions']} | "
            f"{row['reached_box']} | {row['shot_possessions']} | "
            f"{row['xg']:.3f} | {row['goals']} |"
        )

    lines.extend(
        [
            "",
            "## Goal evidence",
            "",
            "| Minute | Team | Scorer | Pattern | xG | Assist | Penalty foul |",
            "| ---: | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for goal in evidence["goals"]:
        assist = goal["key_pass"]["player"] if goal["key_pass"] is not None else "—"
        penalty_foul = "—"
        if goal["penalty_award"] is not None:
            committed = goal["penalty_award"]["foul_committed"]
            penalty_foul = committed["player"] if committed else "recorded"
        lines.append(
            f"| {goal['minute'] + 1} | {goal['team']} | {goal['player']} | "
            f"{goal['play_pattern']} | {goal['shot_xg']:.3f} | "
            f"{assist} | {penalty_foul} |"
        )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            evidence["definitions"]["evidence_boundary"],
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source_root = (args.open_data_root or get_open_data_root()).resolve()
    events_path = source_root / "data" / "events" / f"{args.match_id}.json"
    try:
        with events_path.open() as handle:
            events = json.load(handle)
        evidence = build_match_evidence(events)
        if args.format == "markdown":
            print(_render_markdown(args.match_id, evidence))
        else:
            print(
                json.dumps(
                    {
                        "match_id": args.match_id,
                        "source_path": str(events_path),
                        **evidence,
                    },
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        return 0
    except (EvidenceError, OSError, json.JSONDecodeError) as error:
        print(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
