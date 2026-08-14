"""Source-agnostic Event schema and DiffResult — the part that must survive the spike."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Event:
    """One observed object state, normalized from any broker."""

    source: str  # e.g. "alerce/ztf"
    object_id: str  # e.g. "ZTF26abcdxyz"
    event_type: str  # "new_object" | "mag_change"
    ra: float  # degrees, ICRS
    dec: float  # degrees, ICRS
    object_class: str  # e.g. "SN"
    prob: float  # classifier probability
    mag: float | None  # latest magnitude, if known
    discovered_mjd: float  # first detection
    fetched_at: datetime  # UTC
    payload: str  # raw broker record JSON, for debugging

    def as_row(self) -> tuple:
        d = asdict(self)
        return tuple(d[f] for f in EVENT_FIELDS)


EVENT_FIELDS: tuple[str, ...] = (
    "source",
    "object_id",
    "event_type",
    "ra",
    "dec",
    "object_class",
    "prob",
    "mag",
    "discovered_mjd",
    "fetched_at",
    "payload",
)


@dataclass
class Addition:
    """A `+` line: object never seen in any prior snapshot."""

    object_id: str
    ra: float
    dec: float
    object_class: str
    prob: float
    mag: float | None


@dataclass
class Modification:
    """A `~` line: |mag_today - mag_prev| >= threshold."""

    object_id: str
    ra: float
    dec: float
    object_class: str
    prob: float
    mag: float
    mag_prev: float

    @property
    def delta(self) -> float:
        return self.mag - self.mag_prev


@dataclass
class DiffResult:
    date: str  # YYYY-MM-DD of today's snapshot
    source: str
    baseline: bool  # True when no prior snapshot existed
    additions: list[Addition] = field(default_factory=list)
    modifications: list[Modification] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "source": self.source,
            "baseline": self.baseline,
            "additions": [asdict(a) for a in self.additions],
            "modifications": [
                {**asdict(m), "delta": round(m.delta, 3)} for m in self.modifications
            ],
        }
