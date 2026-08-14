"""Gates 1-2: Parquet partitions round-trip; anti-join diff yields expected + and ~ rows."""

from __future__ import annotations

from pathlib import Path

import duckdb

from skydiff.diff import compute_diff
from skydiff.schema import Event
from skydiff.store import list_partition_dates, write_snapshot

from .conftest import DAY_N, DAY_N1


def test_write_snapshot_roundtrip(tmp_path: Path, day_n_events: list[Event]) -> None:
    path = write_snapshot(day_n_events, tmp_path, DAY_N)
    assert path.exists()
    assert list_partition_dates(tmp_path) == [DAY_N]
    rows = duckdb.query(f"SELECT count(*), count(DISTINCT object_id) FROM '{path}'").fetchone()
    assert rows == (len(day_n_events), len(day_n_events))


def test_baseline_diff_all_additions(tmp_path: Path, day_n_events: list[Event]) -> None:
    write_snapshot(day_n_events, tmp_path, DAY_N)
    result = compute_diff(tmp_path, DAY_N)
    assert result.baseline is True
    assert len(result.additions) == len(day_n_events)
    assert result.modifications == []


def test_day_over_day_diff(
    tmp_path: Path, day_n_events: list[Event], day_n1_events: list[Event]
) -> None:
    write_snapshot(day_n_events, tmp_path, DAY_N)
    write_snapshot(day_n1_events, tmp_path, DAY_N1)
    result = compute_diff(tmp_path, DAY_N1)

    assert result.baseline is False
    # doctored fixture: exactly one brand-new object
    assert [a.object_id for a in result.additions] == ["ZTF26zznewsn"]
    assert result.additions[0].mag == 18.4
    # doctored fixture: exactly one object brightened by 0.5 mag (>= 0.3 threshold)
    assert [m.object_id for m in result.modifications] == ["ZTF26abnuyoi"]
    mod = result.modifications[0]
    assert mod.delta < 0  # brightened
    assert abs(mod.delta) - 0.5 < 1e-6


def test_unchanged_objects_never_reported(
    tmp_path: Path, day_n_events: list[Event], day_n1_events: list[Event]
) -> None:
    write_snapshot(day_n_events, tmp_path, DAY_N)
    write_snapshot(day_n1_events, tmp_path, DAY_N1)
    result = compute_diff(tmp_path, DAY_N1)
    reported = {a.object_id for a in result.additions} | {
        m.object_id for m in result.modifications
    }
    unchanged = {e.object_id for e in day_n_events} - {"ZTF26abnuyoi"}
    assert reported.isdisjoint(unchanged)
