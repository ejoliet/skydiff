"""Stage 5c: render markdown diff and publish via `gh gist` (auth delegated to gh)."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from .schema import DiffResult

GIST_FILENAME = "skydiff.md"


def to_markdown(result: DiffResult) -> str:
    lines = [f"# skydiff · {result.date}", "", f"source: `{result.source}`"]
    if result.baseline:
        lines.append("_(baseline — first run, no prior snapshot)_")
    lines.append("")
    if result.additions:
        lines.append("## Additions")
        lines.append("")
        lines.append("| | object | class | P | mag | ra | dec |")
        lines.append("|---|---|---|---|---|---|---|")
        for a in result.additions:
            mag = f"{a.mag:.1f}" if a.mag is not None else "—"
            lines.append(
                f"| `+` | {a.object_id} | {a.object_class} | {a.prob:.2f} | {mag} "
                f"| {a.ra:.4f} | {a.dec:+.4f} |"
            )
        lines.append("")
    if result.modifications:
        lines.append("## Modifications")
        lines.append("")
        lines.append("| | object | Δmag | mag | prev | ra | dec |")
        lines.append("|---|---|---|---|---|---|---|")
        for m in result.modifications:
            lines.append(
                f"| `~` | {m.object_id} | {m.delta:+.2f} | {m.mag:.1f} | {m.mag_prev:.1f} "
                f"| {m.ra:.4f} | {m.dec:+.4f} |"
            )
        lines.append("")
    lines.append(
        f"{len(result.additions)} additions, {len(result.modifications)} modifications"
    )
    return "\n".join(lines) + "\n"


def publish(result: DiffResult) -> str:
    """Create a gist, or update the one named by SKYDIFF_GIST_ID. Returns gist URL."""
    md = to_markdown(result)
    gist_id = os.environ.get("SKYDIFF_GIST_ID")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / GIST_FILENAME
        path.write_text(md, encoding="utf-8")
        if gist_id:
            # AIDEV: `gh gist edit` is interactive; gh api PATCH updates in place reliably
            subprocess.run(
                [
                    "gh", "api", f"gists/{gist_id}", "-X", "PATCH",
                    "-f", f"files[{GIST_FILENAME}][content]={md}",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return f"https://gist.github.com/{gist_id}"
        proc = subprocess.run(
            ["gh", "gist", "create", str(path), "--desc", f"skydiff · {result.date}"],
            check=True,
            capture_output=True,
            text=True,
        )
    match = re.search(r"https://gist\.github\.com/\S+", proc.stdout + proc.stderr)
    if not match:
        raise RuntimeError(f"gh gist create returned no URL: {proc.stdout!r}")
    return match.group(0)
