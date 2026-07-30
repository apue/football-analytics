"""Command-line interface for the local open-data catalog."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from football_analytics.catalog import (
    CatalogError,
    ensure_catalog,
    execute_readonly_query,
    fetch_matches,
    list_matches,
    list_seasons,
    read_catalog_status,
    resolve_entity,
    stable_views,
)
from football_analytics.paths import (
    get_catalog_path,
    get_open_data_root,
    get_project_root,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="catalog",
        description="Search and materialize Hudl StatsBomb open-data matches.",
    )
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument("--open-data-root", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show local catalog freshness.")
    subparsers.add_parser("refresh", help="Check upstream and rebuild if needed.")

    resolve = subparsers.add_parser("resolve", help="Resolve a name to stable IDs.")
    resolve.add_argument("entity_type", choices=("competition", "manager", "team"))
    resolve.add_argument("query")

    seasons = subparsers.add_parser("seasons", help="List newest available seasons.")
    seasons.add_argument("--competition-id", type=int, required=True)
    seasons.add_argument("--team-id", type=int)
    seasons.add_argument("--limit", type=int)

    matches = subparsers.add_parser("matches", help="List matching games.")
    matches.add_argument("--competition-id", type=int)
    matches.add_argument("--season-id", type=int)
    matches.add_argument("--team-id", type=int)
    matches.add_argument("--manager-id", type=int)
    matches.add_argument(
        "--has-360",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    matches.add_argument("--date-from")
    matches.add_argument("--date-to")
    matches.add_argument("--limit", type=int, default=100)

    sql = subparsers.add_parser("sql", help="Run one read-only catalog query.")
    sql.add_argument("statement")

    fetch = subparsers.add_parser("fetch", help="Materialize confirmed match files.")
    fetch.add_argument("--match-id", type=int, action="append", required=True)
    return parser


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def _ensure_source(source_root: Path) -> None:
    if (source_root / ".git").is_dir():
        return
    script = get_project_root() / "scripts" / "sync_open_data.sh"
    subprocess.run([str(script)], check=True)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source_root = (args.open_data_root or get_open_data_root()).resolve()
    database_path = (args.database or get_catalog_path()).resolve()
    try:
        if args.command == "status":
            payload = {
                "catalog": read_catalog_status(database_path),
                "stable_views": list(stable_views()),
            }
        elif args.command == "fetch":
            payload = fetch_matches(source_root, database_path, args.match_id)
        else:
            _ensure_source(source_root)
            status = ensure_catalog(
                source_root,
                database_path,
                force=args.command == "refresh",
            )
            if args.command == "refresh":
                payload = {"catalog": status}
            elif args.command == "resolve":
                payload = {
                    "catalog": status,
                    "resolution": resolve_entity(
                        database_path,
                        args.entity_type,
                        args.query,
                    ),
                }
            elif args.command == "seasons":
                payload = {
                    "catalog": status,
                    "seasons": list_seasons(
                        database_path,
                        competition_id=args.competition_id,
                        team_id=args.team_id,
                        limit=args.limit,
                    ),
                }
            elif args.command == "matches":
                payload = {
                    "catalog": status,
                    "matches": list_matches(
                        database_path,
                        competition_id=args.competition_id,
                        season_id=args.season_id,
                        team_id=args.team_id,
                        manager_id=args.manager_id,
                        has_360=args.has_360,
                        date_from=args.date_from,
                        date_to=args.date_to,
                        limit=args.limit,
                    ),
                }
            elif args.command == "sql":
                payload = {
                    "catalog": status,
                    "rows": execute_readonly_query(database_path, args.statement),
                }
            else:  # pragma: no cover - argparse guarantees the command.
                raise CatalogError(f"Unsupported command: {args.command}")
        _emit(payload)
        return 0
    except (CatalogError, OSError, subprocess.SubprocessError) as error:
        print(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
