"""Gate 1: normalize maps broker records to valid Events."""

from __future__ import annotations

import json

from skydiff.fetch_alerce import SOURCE, latest_mag
from skydiff.schema import Event


def test_normalize_produces_valid_events(day_n_events: list[Event]) -> None:
    assert len(day_n_events) >= 1
    for e in day_n_events:
        assert e.source == SOURCE
        assert e.object_id.startswith("ZTF")
        assert e.event_type == "new_object"
        assert 0.0 <= e.ra < 360.0
        assert -90.0 <= e.dec <= 90.0
        assert e.object_class == "SN"
        assert 0.0 <= e.prob <= 1.0
        assert e.mag is None or 5.0 < e.mag < 25.0
        assert e.discovered_mjd > 58000
        assert e.fetched_at.tzinfo is not None
        raw = json.loads(e.payload)
        assert raw["object"]["oid"] == e.object_id


def test_latest_mag_prefers_g_band() -> None:
    assert latest_mag([{"fid": 2, "maglast": 20.0}, {"fid": 1, "maglast": 18.5}]) == 18.5
    assert latest_mag([{"fid": 2, "maglast": 20.0}]) == 20.0
    assert latest_mag([]) is None
    assert latest_mag([{"fid": 1, "maglast": None}, {"fid": 2, "maglast": 19.0}]) == 19.0
