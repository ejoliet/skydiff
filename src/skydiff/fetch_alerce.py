"""Stage 1-2: query ALeRCE ZTF API and normalize responses to Events."""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from .schema import Event

SOURCE = "alerce/ztf"
BASE_URL = "https://api.alerce.online/ztf/v1"
TIMEOUT_S = 15.0
RETRIES = 3
PAGE_SIZE = 200
# MJD epoch: 1858-11-17T00:00:00 UTC
_MJD_EPOCH = datetime(1858, 11, 17, tzinfo=UTC)


def mjd_from_datetime(dt: datetime) -> float:
    return (dt - _MJD_EPOCH).total_seconds() / 86400.0


def _get(client: httpx.Client, path: str, params: dict[str, Any] | None = None) -> Any:
    """Single httpx call site: 3 retries, exponential backoff, 15 s timeout."""
    last_exc: Exception | None = None
    for attempt in range(RETRIES):
        try:
            resp = client.get(f"{BASE_URL}{path}", params=params)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < RETRIES - 1:
                time.sleep(2**attempt)
    raise RuntimeError(f"ALeRCE request failed after {RETRIES} attempts: {path}") from last_exc


def latest_mag(magstats: list[dict[str, Any]]) -> float | None:
    """Latest magnitude, preferring g band (fid=1), falling back to r (fid=2)."""
    by_fid = {m.get("fid"): m.get("maglast") for m in magstats}
    for fid in (1, 2):
        if by_fid.get(fid) is not None:
            return float(by_fid[fid])
    return None


def normalize(
    obj: dict[str, Any],
    magstats: list[dict[str, Any]],
    fetched_at: datetime,
) -> Event:
    """Map one ALeRCE object record + its magstats to the generic Event schema."""
    return Event(
        source=SOURCE,
        object_id=str(obj["oid"]),
        event_type="new_object",
        ra=float(obj["meanra"]),
        dec=float(obj["meandec"]),
        object_class=str(obj.get("class", "SN")),
        prob=float(obj.get("probability", 0.0)),
        mag=latest_mag(magstats),
        discovered_mjd=float(obj["firstmjd"]),
        fetched_at=fetched_at,
        payload=json.dumps({"object": obj, "magstats": magstats}, separators=(",", ":")),
    )


def fetch_events(
    since_mjd: float,
    min_prob: float | None = None,
    client: httpx.Client | None = None,
) -> list[Event]:
    """Fetch SN candidates first detected after since_mjd, with latest magnitudes."""
    if min_prob is None:
        min_prob = float(os.environ.get("SKYDIFF_MIN_PROB", "0.5"))
    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=TIMEOUT_S, follow_redirects=True)
    fetched_at = datetime.now(UTC)
    try:
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            data = _get(
                client,
                "/objects/",
                params={
                    "classifier": "stamp_classifier",
                    "class": "SN",
                    "probability": min_prob,
                    "firstmjd": since_mjd,
                    "order_by": "probability",
                    "order_mode": "DESC",
                    "page": page,
                    "page_size": PAGE_SIZE,
                },
            )
            items.extend(data.get("items", []))
            if not data.get("has_next"):
                break
            page += 1
        events = []
        for obj in items:
            magstats = _get(client, f"/objects/{obj['oid']}/magstats")
            events.append(normalize(obj, magstats, fetched_at))
        return events
    finally:
        if owns_client:
            client.close()
