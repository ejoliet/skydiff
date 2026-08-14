"""Stage 4: DuckDB anti-join across daily partitions -> DiffResult."""

from __future__ import annotations

from pathlib import Path

import duckdb

from .fetch_alerce import SOURCE
from .schema import Addition, DiffResult, Modification
from .store import list_partition_dates, partition_path

MAG_DELTA_THRESHOLD = 0.3


def compute_diff(root: Path, today: str) -> DiffResult:
    """Diff today's partition against all prior partitions.

    Additions: object_id absent from every prior snapshot.
    Modifications: |mag_today - mag_latest_prior| >= MAG_DELTA_THRESHOLD.
    First-ever run (no prior partition) -> baseline: everything is an addition.
    """
    dates = list_partition_dates(root)
    if today not in dates:
        raise FileNotFoundError(f"no snapshot for {today} under {root / 'snapshots'}")
    prior_dates = [d for d in dates if d < today]
    today_glob = str(partition_path(root, today))

    con = duckdb.connect()
    try:
        if not prior_dates:
            rows = con.execute(
                f"SELECT object_id, ra, dec, object_class, prob, mag FROM '{today_glob}' "
                "ORDER BY prob DESC"
            ).fetchall()
            return DiffResult(
                date=today,
                source=SOURCE,
                baseline=True,
                additions=[Addition(*r) for r in rows],
            )

        prior_globs = ", ".join(f"'{partition_path(root, d)}'" for d in prior_dates)
        latest_prior = str(partition_path(root, prior_dates[-1]))

        additions = con.execute(
            f"""
            SELECT t.object_id, t.ra, t.dec, t.object_class, t.prob, t.mag
            FROM '{today_glob}' t
            ANTI JOIN read_parquet([{prior_globs}]) p USING (object_id)
            ORDER BY t.prob DESC
            """
        ).fetchall()

        modifications = con.execute(
            f"""
            SELECT t.object_id, t.ra, t.dec, t.object_class, t.prob, t.mag, p.mag AS mag_prev
            FROM '{today_glob}' t
            JOIN '{latest_prior}' p USING (object_id)
            WHERE t.mag IS NOT NULL AND p.mag IS NOT NULL
              AND abs(t.mag - p.mag) >= {MAG_DELTA_THRESHOLD}
            ORDER BY abs(t.mag - p.mag) DESC
            """
        ).fetchall()

        return DiffResult(
            date=today,
            source=SOURCE,
            baseline=False,
            additions=[Addition(*r) for r in additions],
            modifications=[Modification(*r) for r in modifications],
        )
    finally:
        con.close()
