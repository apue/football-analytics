"""Command-line entry point for auditable Firecrawl evidence search."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .evidence_search import (
    EvidenceSearchError,
    FirecrawlSearchClient,
    load_firecrawl_config,
    load_search_config,
    replay_evidence_search,
    run_evidence_search,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run one configured search and print its non-secret validation summary."""

    parser = argparse.ArgumentParser(prog="evidence-search")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--replay-raw-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        search_config = load_search_config(args.config)
        if args.replay_raw_dir is not None:
            summary = replay_evidence_search(
                search_config, args.replay_raw_dir, args.output_dir
            )
        else:
            client = FirecrawlSearchClient(load_firecrawl_config())
            summary = run_evidence_search(search_config, client, args.output_dir)
    except EvidenceSearchError as exc:
        parser.error(str(exc))
    print(json.dumps(summary, sort_keys=True))
    return 0
