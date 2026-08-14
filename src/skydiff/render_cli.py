"""Stage 5a: rich terminal diff output."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from .schema import DiffResult


def _fmt_coord(ra: float, dec: float) -> str:
    return f"ra={ra:.2f} dec={dec:+.2f}"


def render(result: DiffResult, dashboard: str | None = None, gist: str | None = None) -> None:
    console = Console(highlight=False)
    header = f"skydiff · {result.date} · source: {result.source}"
    if result.baseline:
        header += " · (baseline)"
    console.print(header, style="bold")
    console.print()

    for a in result.additions:
        line = Text()
        line.append(f"+ {a.object_id:<14}", style="green")
        label = "new SN candidate" if a.object_class == "SN" else f"new {a.object_class}"
        mag = f"g={a.mag:.1f}" if a.mag is not None else "mag=?"
        line.append(f" {label}  (P={a.prob:.2f}, {mag}, {_fmt_coord(a.ra, a.dec)})")
        console.print(line)

    for m in result.modifications:
        line = Text()
        line.append(f"~ {m.object_id:<14}", style="yellow")
        verb = "brightened" if m.delta < 0 else "faded"
        line.append(
            f" {verb} {abs(m.delta):.1f} mag since yesterday (g={m.mag:.1f})"
        )
        console.print(line)

    console.print()
    summary = (
        f"{len(result.additions)} additions, {len(result.modifications)} modifications"
    )
    extras = [f"dashboard: {dashboard}" if dashboard else None, f"gist: {gist}" if gist else None]
    tail = " · ".join([summary, *[e for e in extras if e]])
    console.print(tail, style="dim")
