"""Stage 5b: inject diff JSON into site/template.html -> site/index.html."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import DiffResult

_OPEN = '<script id="skydiff-data" type="application/json">'
_CLOSE = "</script>"


def render_html(result: DiffResult, site_dir: Path) -> Path:
    template = (site_dir / "template.html").read_text(encoding="utf-8")
    start = template.find(_OPEN)
    if start == -1:
        raise ValueError("skydiff-data block not found in template.html")
    end = template.index(_CLOSE, start)
    payload = json.dumps(result.to_dict(), indent=1)
    # AIDEV: escape "</" so payload content can never terminate the script block early
    payload = payload.replace("</", "<\\/")
    html = template[: start + len(_OPEN)] + "\n" + payload + "\n" + template[end:]
    out = site_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    return out
