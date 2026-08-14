"""Stage 3: append daily snapshots as Parquet partitions under data/snapshots/."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

from .schema import EVENT_FIELDS, Event

_DDL = """
CREATE TABLE events (
    source VARCHAR,
    object_id VARCHAR,
    event_type VARCHAR,
    ra DOUBLE,
    dec DOUBLE,
    object_class VARCHAR,
    prob DOUBLE,
    mag DOUBLE,
    discovered_mjd DOUBLE,
    fetched_at TIMESTAMPTZ,
    payload VARCHAR
)
"""


def data_dir() -> Path:
    return Path(os.environ.get("SKYDIFF_DATA_DIR", "./data"))


def partition_path(root: Path, date: str) -> Path:
    return root / "snapshots" / f"date={date}" / "events.parquet"


def write_snapshot(events: list[Event], root: Path, date: str) -> Path:
    """Write (or overwrite, on same-day re-run) one daily Parquet partition."""
    path = partition_path(root, date)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(_DDL)
    placeholders = ",".join("?" for _ in EVENT_FIELDS)
    con.executemany(
        f"INSERT INTO events VALUES ({placeholders})",
        [e.as_row() for e in events],
    )
    con.execute(f"COPY events TO '{path}' (FORMAT PARQUET)")
    con.close()
    return path


def list_partition_dates(root: Path) -> list[str]:
    """Snapshot dates present on disk, ascending."""
    snap = root / "snapshots"
    if not snap.is_dir():
        return []
    dates = [
        p.name.removeprefix("date=")
        for p in snap.iterdir()
        if p.is_dir() and p.name.startswith("date=") and (p / "events.parquet").exists()
    ]
    return sorted(dates)
