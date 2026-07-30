"""Queryable local catalog for Hudl StatsBomb open-data metadata."""

from __future__ import annotations

import difflib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import unicodedata
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from football_analytics.paths import get_project_root

CATALOG_TTL = timedelta(days=7)
RETRY_BACKOFF = timedelta(hours=1)
SCHEMA_VERSION = 3
ENTITY_KINDS = {"competition", "manager", "team"}


class CatalogError(RuntimeError):
    """Raised when the catalog cannot safely satisfy a request."""


def normalize_search(value: str) -> str:
    """Normalize case, accents, punctuation, and whitespace for name search."""
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return " ".join(re.sub(r"[^\w]+", " ", value).split())


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat() if value else None


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _git(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise CatalogError(f"Git command failed ({' '.join(args)}): {detail}")
    return result


def _commit(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _is_sparse(root: Path) -> bool:
    result = _git(root, "config", "--bool", "core.sparseCheckout", check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def _add_sparse_patterns(root: Path, patterns: Sequence[str]) -> None:
    if _is_sparse(root):
        _git(root, "sparse-checkout", "add", *patterns)


def _ensure_metadata(root: Path) -> None:
    _add_sparse_patterns(
        root,
        [
            "/README.md",
            "/LICENSE.pdf",
            "/data/competitions.json",
            "/data/matches/",
        ],
    )


def _available_ids(root: Path, directory: str) -> set[int]:
    result = _git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        f"HEAD:data/{directory}",
        check=False,
    )
    if result.returncode:
        return set()
    return {
        int(Path(item).stem)
        for item in result.stdout.splitlines()
        if Path(item).stem.isdigit()
    }


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE catalog_sync (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  schema_version INTEGER NOT NULL,
  source_url TEXT NOT NULL,
  source_commit TEXT NOT NULL,
  last_attempted_at TEXT,
  last_successful_check_at TEXT,
  last_rebuilt_at TEXT NOT NULL,
  last_result TEXT NOT NULL,
  last_error TEXT
);
CREATE TABLE entities (
  kind TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  search_name TEXT NOT NULL,
  PRIMARY KEY (kind, entity_id)
);
CREATE TABLE entity_names (
  kind TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  search_name TEXT NOT NULL,
  name_kind TEXT NOT NULL,
  PRIMARY KEY (kind, entity_id, search_name),
  FOREIGN KEY (kind, entity_id) REFERENCES entities(kind, entity_id)
);
CREATE INDEX entity_names_search_idx ON entity_names(kind, search_name);
CREATE TABLE seasons (
  competition_id INTEGER NOT NULL,
  season_id INTEGER NOT NULL,
  season_name TEXT NOT NULL,
  first_match_date TEXT,
  last_match_date TEXT,
  available_match_count INTEGER NOT NULL DEFAULT 0,
  event_match_count INTEGER NOT NULL DEFAULT 0,
  lineup_match_count INTEGER NOT NULL DEFAULT 0,
  three_sixty_match_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (competition_id, season_id)
);
CREATE TABLE matches (
  match_id INTEGER PRIMARY KEY,
  competition_id INTEGER NOT NULL,
  season_id INTEGER NOT NULL,
  match_date TEXT NOT NULL,
  home_team_id INTEGER NOT NULL,
  away_team_id INTEGER NOT NULL,
  home_score INTEGER,
  away_score INTEGER,
  has_events INTEGER NOT NULL,
  has_lineups INTEGER NOT NULL,
  has_360 INTEGER NOT NULL
);
CREATE INDEX matches_scope_idx
  ON matches(competition_id, season_id, match_date);
CREATE TABLE match_managers (
  match_id INTEGER NOT NULL,
  team_id INTEGER NOT NULL,
  manager_id INTEGER NOT NULL,
  PRIMARY KEY (match_id, team_id, manager_id)
);
CREATE VIEW catalog_competition_seasons AS
SELECT s.*, c.name AS competition_name,
       'unverified' AS coverage_status
FROM seasons s
JOIN entities c
  ON c.kind = 'competition' AND c.entity_id = s.competition_id;
CREATE VIEW catalog_matches AS
SELECT m.*, c.name AS competition_name, s.season_name,
       home.name AS home_team_name, away.name AS away_team_name
FROM matches m
JOIN seasons s USING (competition_id, season_id)
JOIN entities c
  ON c.kind = 'competition' AND c.entity_id = m.competition_id
JOIN entities home
  ON home.kind = 'team' AND home.entity_id = m.home_team_id
JOIN entities away
  ON away.kind = 'team' AND away.entity_id = m.away_team_id;
CREATE VIEW catalog_match_managers AS
SELECT mm.*, team.name AS team_name, manager.name AS manager_name
FROM match_managers mm
JOIN entities team
  ON team.kind = 'team' AND team.entity_id = mm.team_id
JOIN entities manager
  ON manager.kind = 'manager' AND manager.entity_id = mm.manager_id;
CREATE VIEW catalog_team_seasons AS
WITH team_matches AS (
  SELECT match_id, competition_id, season_id, home_team_id AS team_id
  FROM matches
  UNION ALL
  SELECT match_id, competition_id, season_id, away_team_id AS team_id
  FROM matches
)
SELECT tm.competition_id, c.name AS competition_name,
       tm.season_id, s.season_name, tm.team_id, team.name AS team_name,
       MIN(m.match_date) AS first_match_date,
       MAX(m.match_date) AS last_match_date,
       COUNT(*) AS available_match_count,
       SUM(m.has_events) AS event_match_count,
       SUM(m.has_lineups) AS lineup_match_count,
       SUM(m.has_360) AS three_sixty_match_count,
       'unverified' AS coverage_status
FROM team_matches tm
JOIN matches m USING (match_id)
JOIN seasons s USING (competition_id, season_id)
JOIN entities c
  ON c.kind = 'competition' AND c.entity_id = tm.competition_id
JOIN entities team
  ON team.kind = 'team' AND team.entity_id = tm.team_id
GROUP BY tm.competition_id, tm.season_id, tm.team_id;
"""

STABLE_VIEWS = (
    "catalog_competition_seasons",
    "catalog_team_seasons",
    "catalog_matches",
    "catalog_match_managers",
)


def _connect(path: Path, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        connection = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=ro",
            uri=True,
        )
        connection.execute("PRAGMA query_only = ON")
    else:
        connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _put_entity(
    connection: sqlite3.Connection,
    kind: str,
    entity_id: int,
    name: str,
    extra_names: Sequence[tuple[str | None, str]] = (),
) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO entities VALUES (?, ?, ?, ?)",
        (kind, entity_id, name, normalize_search(name)),
    )
    for candidate, name_kind in ((name, "canonical"), *extra_names):
        if candidate:
            connection.execute(
                "INSERT OR IGNORE INTO entity_names VALUES (?, ?, ?, ?, ?)",
                (kind, entity_id, candidate, normalize_search(candidate), name_kind),
            )


def _aliases(path: Path | None) -> dict[str, dict[str, list[str]]]:
    path = path or get_project_root() / "config" / "open_data_aliases.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def _source_url(root: Path) -> str:
    result = _git(root, "remote", "get-url", "origin", check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def build_catalog(
    source_root: Path,
    database_path: Path,
    *,
    alias_path: Path | None = None,
    now: datetime | None = None,
    last_attempted_at: datetime | None = None,
    last_successful_check_at: datetime | None = None,
    result: str = "rebuilt",
    error: str | None = None,
) -> dict[str, Any]:
    """Build a complete temporary database and atomically replace the catalog."""
    now = now or datetime.now(UTC)
    source_root, database_path = source_root.resolve(), database_path.resolve()
    competition_file = source_root / "data" / "competitions.json"
    match_root = source_root / "data" / "matches"
    if not competition_file.is_file() or not match_root.is_dir():
        raise CatalogError(
            "Competition and match metadata are missing; "
            "run ./scripts/sync_open_data.sh."
        )

    availability = {
        "events": _available_ids(source_root, "events"),
        "lineups": _available_ids(source_root, "lineups"),
        "360": _available_ids(source_root, "three-sixty"),
    }
    database_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{database_path.name}.",
        suffix=".tmp",
        dir=database_path.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)

    try:
        connection = sqlite3.connect(temporary)
        connection.executescript(SCHEMA)
        with connection:
            for item in json.loads(competition_file.read_text()):
                competition_id = int(item["competition_id"])
                _put_entity(
                    connection,
                    "competition",
                    competition_id,
                    item["competition_name"],
                )
                connection.execute(
                    "INSERT OR REPLACE INTO seasons "
                    "(competition_id, season_id, season_name) VALUES (?, ?, ?)",
                    (competition_id, int(item["season_id"]), item["season_name"]),
                )

            for path in sorted(match_root.glob("*/*.json")):
                competition_id, season_id = int(path.parent.name), int(path.stem)
                for item in json.loads(path.read_text()):
                    match_id = int(item["match_id"])
                    team_ids: dict[str, int] = {}
                    for side in ("home", "away"):
                        team = item[f"{side}_team"]
                        team_id = int(team[f"{side}_team_id"])
                        team_ids[side] = team_id
                        _put_entity(
                            connection,
                            "team",
                            team_id,
                            team[f"{side}_team_name"],
                        )
                        for manager in team.get("managers") or []:
                            manager_id = int(manager["id"])
                            _put_entity(
                                connection,
                                "manager",
                                manager_id,
                                manager["name"],
                                [(manager.get("nickname"), "nickname")],
                            )
                            connection.execute(
                                "INSERT OR IGNORE INTO match_managers VALUES (?, ?, ?)",
                                (match_id, team_id, manager_id),
                            )
                    connection.execute(
                        "INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            match_id,
                            competition_id,
                            season_id,
                            item["match_date"],
                            team_ids["home"],
                            team_ids["away"],
                            item.get("home_score"),
                            item.get("away_score"),
                            int(match_id in availability["events"]),
                            int(match_id in availability["lineups"]),
                            int(match_id in availability["360"]),
                        ),
                    )

            connection.execute(
                """
                UPDATE seasons SET
                  first_match_date = (
                    SELECT MIN(match_date) FROM matches m
                    WHERE (m.competition_id, m.season_id) =
                          (seasons.competition_id, seasons.season_id)),
                  last_match_date = (
                    SELECT MAX(match_date) FROM matches m
                    WHERE (m.competition_id, m.season_id) =
                          (seasons.competition_id, seasons.season_id)),
                  available_match_count = (
                    SELECT COUNT(*) FROM matches m
                    WHERE (m.competition_id, m.season_id) =
                          (seasons.competition_id, seasons.season_id)),
                  event_match_count = (
                    SELECT COALESCE(SUM(has_events), 0) FROM matches m
                    WHERE (m.competition_id, m.season_id) =
                          (seasons.competition_id, seasons.season_id)),
                  lineup_match_count = (
                    SELECT COALESCE(SUM(has_lineups), 0) FROM matches m
                    WHERE (m.competition_id, m.season_id) =
                          (seasons.competition_id, seasons.season_id)),
                  three_sixty_match_count = (
                    SELECT COALESCE(SUM(has_360), 0) FROM matches m
                    WHERE (m.competition_id, m.season_id) =
                          (seasons.competition_id, seasons.season_id))
                """
            )
            group_to_kind = {
                "competitions": "competition",
                "managers": "manager",
                "teams": "team",
            }
            for group, entries in _aliases(alias_path).items():
                kind = group_to_kind[group]
                for entity_id, names in entries.items():
                    entity = connection.execute(
                        "SELECT name FROM entities WHERE kind = ? AND entity_id = ?",
                        (kind, int(entity_id)),
                    ).fetchone()
                    if entity:
                        _put_entity(
                            connection,
                            kind,
                            int(entity_id),
                            entity[0],
                            [(name, "alias") for name in names],
                        )
            connection.execute(
                "INSERT INTO catalog_sync VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    SCHEMA_VERSION,
                    _source_url(source_root),
                    _commit(source_root),
                    _iso(last_attempted_at),
                    _iso(last_successful_check_at),
                    _iso(now),
                    result,
                    error,
                ),
            )
        connection.close()
        os.replace(temporary, database_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return read_catalog_status(database_path, now=now)


def read_catalog_status(
    database_path: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Read local sync metadata without network access."""
    if not database_path.is_file():
        return {"exists": False, "stale": True}
    with _connect(database_path, readonly=True) as connection:
        row = connection.execute("SELECT * FROM catalog_sync").fetchone()
    if row is None:
        raise CatalogError("Catalog has no sync record.")
    status = dict(row)
    checked = _parse_time(status["last_successful_check_at"])
    status["exists"] = True
    status["stale"] = (
        checked is None or (now or datetime.now(UTC)) - checked >= CATALOG_TTL
    )
    return status


def _record_sync(
    database_path: Path,
    now: datetime,
    result: str,
    error: str | None = None,
) -> None:
    successful = _iso(now) if result == "unchanged" else None
    with _connect(database_path) as connection:
        connection.execute(
            "UPDATE catalog_sync SET last_attempted_at = ?, "
            "last_successful_check_at = COALESCE(?, last_successful_check_at), "
            "last_result = ?, last_error = ?",
            (_iso(now), successful, result, error),
        )


def _sync_upstream(source_root: Path) -> bool:
    _git(source_root, "fetch", "origin")
    upstream = _git(source_root, "rev-parse", "@{upstream}").stdout.strip()
    current = _commit(source_root)
    if upstream != current:
        ancestor = _git(
            source_root,
            "merge-base",
            "--is-ancestor",
            current,
            upstream,
            check=False,
        )
        if ancestor.returncode:
            raise CatalogError("Open-data checkout cannot be fast-forwarded.")
        _git(source_root, "merge", "--ff-only", upstream)
    _ensure_metadata(source_root)
    return upstream != current


def ensure_catalog(
    source_root: Path,
    database_path: Path,
    *,
    alias_path: Path | None = None,
    force: bool = False,
    now: datetime | None = None,
    sync_upstream: Callable[[Path], bool] = _sync_upstream,
) -> dict[str, Any]:
    """Ensure the local catalog is built and no more than seven days stale."""
    now = now or datetime.now(UTC)
    status = read_catalog_status(database_path, now=now)
    schema_changed = status["exists"] and status.get("schema_version") != SCHEMA_VERSION
    if status["exists"] and not force and not status["stale"] and not schema_changed:
        return {**status, "action": "fresh"}
    if status["exists"] and not force and status["last_result"] == "failed":
        attempted = _parse_time(status["last_attempted_at"])
        if attempted and now - attempted < RETRY_BACKOFF:
            return {**status, "action": "backoff"}

    try:
        changed = sync_upstream(source_root)
    except CatalogError as error:
        if status["exists"]:
            _record_sync(database_path, now, "failed", str(error))
            return {**read_catalog_status(database_path, now=now), "action": "failed"}
        _ensure_metadata(source_root)
        return {
            **build_catalog(
                source_root,
                database_path,
                alias_path=alias_path,
                now=now,
                last_attempted_at=now,
                result="failed",
                error=str(error),
            ),
            "action": "built_offline",
        }

    source_changed = (
        status["exists"] and _commit(source_root) != status["source_commit"]
    )
    if force or not status["exists"] or changed or source_changed or schema_changed:
        return {
            **build_catalog(
                source_root,
                database_path,
                alias_path=alias_path,
                now=now,
                last_attempted_at=now,
                last_successful_check_at=now,
            ),
            "action": "rebuilt",
        }
    _record_sync(database_path, now, "unchanged")
    return {**read_catalog_status(database_path, now=now), "action": "unchanged"}


def resolve_entity(
    database_path: Path, entity_type: str, query: str, *, limit: int = 5
) -> dict[str, Any]:
    """Return an exact ID or ranked candidates without silent fuzzy selection."""
    if entity_type not in ENTITY_KINDS:
        raise CatalogError(f"Unsupported entity type: {entity_type}")
    search_query = normalize_search(query)
    if not search_query:
        raise CatalogError("Search query cannot be empty.")
    with _connect(database_path, readonly=True) as connection:
        exact = connection.execute(
            """
            SELECT n.entity_id, e.name, n.name matched_name, n.name_kind
            FROM entity_names n JOIN entities e USING (kind, entity_id)
            WHERE n.kind = ? AND n.search_name = ?
            ORDER BY e.name
            """,
            (entity_type, search_query),
        ).fetchall()
        if len({row["entity_id"] for row in exact}) == 1:
            row = exact[0]
            candidates = [
                {
                    "id": row["entity_id"],
                    "name": row["name"],
                    "matched_name": row["matched_name"],
                    "method": row["name_kind"],
                    "score": 1.0,
                }
            ]
            status = "resolved"
        else:
            rows = connection.execute(
                """
                SELECT n.entity_id, e.name, n.name matched_name, n.search_name
                FROM entity_names n JOIN entities e USING (kind, entity_id)
                WHERE n.kind = ?
                """,
                (entity_type,),
            ).fetchall()
            best: dict[int, dict[str, Any]] = {}
            for row in rows:
                terms = [row["search_name"], *row["search_name"].split()]
                substring = (
                    search_query in row["search_name"]
                    or row["search_name"] in search_query
                )
                score = max(
                    0.9 if substring else 0,
                    *(
                        difflib.SequenceMatcher(None, search_query, term).ratio()
                        for term in terms
                    ),
                )
                candidate = {
                    "id": row["entity_id"],
                    "name": row["name"],
                    "matched_name": row["matched_name"],
                    "method": "substring" if substring else "fuzzy",
                    "score": round(score, 3),
                }
                if score >= 0.62 and (
                    row["entity_id"] not in best
                    or candidate["score"] > best[row["entity_id"]]["score"]
                ):
                    best[row["entity_id"]] = candidate
            candidates = sorted(
                best.values(), key=lambda item: (-item["score"], item["name"])
            )[:limit]
            status = "resolution_required" if candidates else "not_found"
    return {
        "status": status,
        "entity_type": entity_type,
        "query": query,
        "normalized_query": search_query,
        "candidates": candidates,
    }


def _rows(database_path: Path, query: str, parameters: Sequence[Any]) -> list[dict]:
    with _connect(database_path, readonly=True) as connection:
        return [dict(row) for row in connection.execute(query, parameters)]


def list_seasons(
    database_path: Path,
    *,
    competition_id: int,
    team_id: int | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """List eligible seasons by actual latest match date."""
    view = (
        "catalog_team_seasons" if team_id is not None else "catalog_competition_seasons"
    )
    where, parameters = "competition_id = ?", [competition_id]
    if team_id is not None:
        where += " AND team_id = ?"
        parameters.append(team_id)
    query = f"SELECT * FROM {view} WHERE {where} ORDER BY last_match_date DESC"
    if limit is not None:
        query += " LIMIT ?"
        parameters.append(limit)
    return _rows(database_path, query, parameters)


def list_matches(
    database_path: Path,
    *,
    competition_id: int | None = None,
    season_id: int | None = None,
    team_id: int | None = None,
    manager_id: int | None = None,
    has_360: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int | None = 100,
) -> list[dict[str, Any]]:
    """List matches using structured filters."""
    clauses, parameters = [], []
    for column, value in (
        ("m.competition_id", competition_id),
        ("m.season_id", season_id),
        ("m.has_360", None if has_360 is None else int(has_360)),
    ):
        if value is not None:
            clauses.append(f"{column} = ?")
            parameters.append(value)
    if manager_id is not None:
        relation = (
            "EXISTS (SELECT 1 FROM match_managers mm "
            "WHERE mm.match_id = m.match_id AND mm.manager_id = ?"
        )
        parameters.append(manager_id)
        if team_id is not None:
            relation += " AND mm.team_id = ?"
            parameters.append(team_id)
        clauses.append(relation + ")")
    elif team_id is not None:
        clauses.append("(m.home_team_id = ? OR m.away_team_id = ?)")
        parameters.extend((team_id, team_id))
    for operator, value in ((">=", date_from), ("<=", date_to)):
        if value:
            clauses.append(f"m.match_date {operator} ?")
            parameters.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT m.* FROM catalog_matches m {where} ORDER BY match_date, match_id"
    if limit is not None:
        query += " LIMIT ?"
        parameters.append(limit)
    return _rows(database_path, query, parameters)


def execute_readonly_query(database_path: Path, statement: str) -> list[dict[str, Any]]:
    """Execute one read-only SELECT/WITH statement."""
    leading = statement.lstrip().split(None, 1)
    if not leading or leading[0].casefold() not in {"select", "with"}:
        raise CatalogError("Read-only SQL must start with SELECT or WITH.")
    try:
        return _rows(database_path, statement, [])
    except sqlite3.Error as error:
        raise CatalogError(f"Read-only SQL failed: {error}") from error


def fetch_matches(
    source_root: Path, database_path: Path, match_ids: Sequence[int]
) -> dict[str, Any]:
    """Materialize detailed files for confirmed IDs at the catalog commit."""
    if not match_ids:
        raise CatalogError("At least one match ID is required.")
    status = read_catalog_status(database_path)
    if _commit(source_root) != status["source_commit"]:
        raise CatalogError(
            "Open-data checkout and catalog commits differ; refresh the catalog."
        )
    placeholders = ",".join("?" for _ in match_ids)
    rows = _rows(
        database_path,
        f"SELECT match_id, has_events, has_lineups, has_360 "
        f"FROM matches WHERE match_id IN ({placeholders})",
        match_ids,
    )
    indexed = {row["match_id"]: row for row in rows}
    missing = sorted(set(match_ids) - set(indexed))
    if missing:
        raise CatalogError(f"Unknown match IDs: {missing}")

    patterns, matches = [], []
    for match_id in dict.fromkeys(match_ids):
        files: dict[str, str | None] = {}
        for label, directory, available in (
            ("events", "events", indexed[match_id]["has_events"]),
            ("lineups", "lineups", indexed[match_id]["has_lineups"]),
            ("three_sixty", "three-sixty", indexed[match_id]["has_360"]),
        ):
            relative = f"data/{directory}/{match_id}.json"
            files[label] = str(source_root / relative) if available else None
            if available:
                patterns.append(f"/{relative}")
        matches.append({"match_id": match_id, "files": files})
    _add_sparse_patterns(source_root, patterns)
    absent = [
        path
        for item in matches
        for path in item["files"].values()
        if path and not Path(path).is_file()
    ]
    if absent:
        raise CatalogError(f"Expected files were not materialized: {absent}")
    return {"source_commit": status["source_commit"], "matches": matches}


def stable_views() -> Sequence[str]:
    """Return the documented read-only view names."""
    return STABLE_VIEWS
