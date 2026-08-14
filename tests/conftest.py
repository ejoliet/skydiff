"""Shared fixtures: canned ALeRCE responses for day N and doctored day N+1.

Tests never hit the live API — these files were captured at Gate 0.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from skydiff.fetch_alerce import normalize
from skydiff.schema import Event

FIXTURES = Path(__file__).parent / "fixtures"

DAY_N = "2026-08-12"
DAY_N1 = "2026-08-13"


def _load_events(objects_file: str, magstats_file: str, fetched_at: datetime) -> list[Event]:
    objects = json.loads((FIXTURES / objects_file).read_text())
    magstats = json.loads((FIXTURES / magstats_file).read_text())
    return [normalize(obj, magstats[obj["oid"]], fetched_at) for obj in objects["items"]]


@pytest.fixture()
def day_n_events() -> list[Event]:
    return _load_events(
        "day_n_objects.json",
        "day_n_magstats.json",
        datetime(2026, 8, 12, 6, 0, tzinfo=UTC),
    )


@pytest.fixture()
def day_n1_events() -> list[Event]:
    return _load_events(
        "day_n1_objects.json",
        "day_n1_magstats.json",
        datetime(2026, 8, 13, 6, 0, tzinfo=UTC),
    )
