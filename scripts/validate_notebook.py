#!/usr/bin/env python3
"""Execute a notebook in memory from a clean kernel."""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "notebook",
        nargs="?",
        type=Path,
        default=ROOT / "course" / "templates" / "analysis.ipynb",
    )
    args = parser.parse_args()
    notebook_path = args.notebook.resolve()

    with notebook_path.open() as handle:
        notebook = nbformat.read(handle, as_version=4)

    client = NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    client.execute()
    print(f"Notebook executed successfully: {notebook_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
