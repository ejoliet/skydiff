"""Entrypoint: skydiff --since yesterday [--html] [--publish] [--json]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .diff import compute_diff
from .fetch_alerce import fetch_events, mjd_from_datetime
from .render_cli import render
from .render_html import render_html
from .store import data_dir, write_snapshot


def since_to_mjd(since: str, now: datetime) -> float:
    """Window start as MJD.

    AIDEV: window semantics (RDD open question, resolved at Gate 1):
    "yesterday" = rolling now-24h; an ISO date = that civil date at 00:00 UTC.
    """
    if since == "yesterday":
        return mjd_from_datetime(now - timedelta(hours=24))
    try:
        dt = datetime.fromisoformat(since).replace(tzinfo=UTC)
    except ValueError as exc:
        raise SystemExit(f"--since must be 'yesterday' or ISO date, got {since!r}") from exc
    return mjd_from_datetime(dt)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skydiff", description="git log for the universe")
    parser.add_argument("--since", default="yesterday", help="window start (yesterday | ISO date)")
    parser.add_argument("--html", action="store_true", help="write site/index.html")
    parser.add_argument("--publish", action="store_true", help="create/update gist via gh")
    parser.add_argument("--json", action="store_true", help="emit DiffResult JSON to stdout")
    args = parser.parse_args(argv)

    now = datetime.now(UTC)
    today = now.date().isoformat()
    root = data_dir()

    events = fetch_events(since_mjd=since_to_mjd(args.since, now))
    write_snapshot(events, root, today)
    result = compute_diff(root, today)

    dashboard: str | None = None
    if args.html:
        # AIDEV: prefer ./site (fresh-clone run from repo root); fall back to repo-relative
        site_dir = Path("site")
        if not (site_dir / "template.html").exists():
            site_dir = Path(__file__).resolve().parents[2] / "site"
        dashboard = str(render_html(result, site_dir))

    gist: str | None = None
    if args.publish:
        from .publish_gist import publish

        gist = publish(result)

    if args.json:
        out = result.to_dict()
        out["dashboard"] = dashboard
        out["gist"] = gist
        json.dump(out, sys.stdout, indent=1)
        sys.stdout.write("\n")
    else:
        render(result, dashboard=dashboard, gist=gist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
