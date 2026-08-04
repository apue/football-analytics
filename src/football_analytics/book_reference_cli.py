"""Command-line interface for the pinned book companion repository."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from football_analytics.book_reference import (
    BookReferenceError,
    load_reference_spec,
    reference_status,
    search_reference,
    show_reference,
    sync_reference,
)
from football_analytics.paths import get_book_reference_root, get_project_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="book-ref",
        description="Query a pinned local Soccer Analytics ML companion repository.",
    )
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--manifest", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Report checkout and pin status.")
    subparsers.add_parser("sync", help="Materialize the manifest commit explicitly.")

    search = subparsers.add_parser("search", help="Search source cells and text files.")
    search.add_argument("query")
    search.add_argument("--chapter")
    search.add_argument("--cell-type", choices=("code", "markdown", "raw"))
    search.add_argument("--regex", action="store_true")
    search.add_argument("--limit", type=int, default=20)

    show = subparsers.add_parser("show", help="Show a file or notebook cell.")
    show.add_argument("path")
    show.add_argument("--cell", type=int)
    return parser


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    project_root = get_project_root()
    repository = (args.repository or get_book_reference_root(project_root)).resolve()
    manifest = (args.manifest or project_root / "references" / "sources.toml").resolve()
    try:
        spec = load_reference_spec(manifest)
        if args.command == "status":
            payload = {"reference": reference_status(repository, spec)}
        elif args.command == "sync":
            payload = {"reference": sync_reference(repository, spec)}
        elif args.command == "search":
            payload = {
                "reference": reference_status(repository, spec),
                "query": args.query,
                "matches": search_reference(
                    repository,
                    spec,
                    args.query,
                    chapter=args.chapter,
                    cell_type=args.cell_type,
                    regex=args.regex,
                    limit=args.limit,
                ),
            }
        elif args.command == "show":
            payload = {
                "reference": reference_status(repository, spec),
                "result": show_reference(
                    repository,
                    spec,
                    args.path,
                    cell=args.cell,
                ),
            }
        else:  # pragma: no cover - argparse guarantees the command.
            raise BookReferenceError(f"Unsupported command: {args.command}")
        _emit(payload)
        return 0
    except (BookReferenceError, OSError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
