"""Gates 3-5: CLI/HTML/markdown renders from one DiffResult."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from skydiff.publish_gist import to_markdown
from skydiff.render_cli import render
from skydiff.render_html import render_html
from skydiff.schema import Addition, DiffResult, Modification

SITE = Path(__file__).parents[1] / "site"


def _sample() -> DiffResult:
    return DiffResult(
        date="2026-08-13",
        source="alerce/ztf",
        baseline=False,
        additions=[Addition("ZTF26abcdxyz", 214.31, 33.02, "SN", 0.87, 18.4)],
        modifications=[Modification("ZTF26aazzqrs", 10.0, -5.0, "SN", 0.9, 17.8, 18.2)],
    )


def test_cli_render_matches_rdd_example(capsys) -> None:  # noqa: ANN001
    render(_sample(), dashboard="site/index.html", gist="https://gist.github.com/x")
    out = capsys.readouterr().out
    assert "skydiff · 2026-08-13 · source: alerce/ztf" in out
    assert "+ ZTF26abcdxyz" in out
    assert "new SN candidate  (P=0.87, g=18.4, ra=214.31 dec=+33.02)" in out
    assert "~ ZTF26aazzqrs" in out
    assert "brightened 0.4 mag since yesterday (g=17.8)" in out
    assert "1 additions, 1 modifications" in out


def test_html_render_injects_data(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    shutil.copy(SITE / "template.html", site_dir / "template.html")
    out = render_html(_sample(), site_dir)
    html = out.read_text()
    start = html.index('<script id="skydiff-data" type="application/json">')
    end = html.index("</script>", start)
    block = html[start:end].split(">", 1)[1]
    data = json.loads(block.replace("<\\/", "</"))
    assert data["additions"][0]["ra"] == 214.31
    assert data["modifications"][0]["delta"] == -0.4
    assert "aladin" in html.lower()


def test_markdown_render(capsys) -> None:  # noqa: ANN001
    md = to_markdown(_sample())
    assert "# skydiff · 2026-08-13" in md
    assert "ZTF26abcdxyz" in md
    assert "-0.40" in md
    assert "1 additions, 1 modifications" in md
