# skydiff (spike-1)

> `git log` for the universe. This spike proves one end-to-end slice: new supernova candidates discovered last night → nightly diff → CLI output, static dashboard, published gist.

**Status**: spike built 2026-08-13. All gates (0–5) pass. See "Spike results" below.

## Quick start

```bash
uv sync
uv run skydiff --since yesterday            # terminal diff
uv run skydiff --since yesterday --html     # + site/index.html (Aladin Lite sky map)
uv run skydiff --since yesterday --publish  # + gist (requires `gh auth login`)
uv run skydiff --json                       # machine mode
```

First run bootstraps: no prior snapshot → everything is `+`, labeled `(baseline)`.

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `SKYDIFF_MIN_PROB` | `0.5` | stamp-classifier probability floor |
| `SKYDIFF_DATA_DIR` | `./data` | snapshot root |
| `SKYDIFF_GIST_ID` | unset | if set, update this gist in place instead of creating new |

## Architecture

```
ALeRCE ZTF API ──▶ fetch ──▶ normalize ──▶ DuckDB/Parquet state ──▶ diff
                                                                     │
                                              ┌──────────────────────┤
                                              ▼            ▼         ▼
                                          CLI (rich)   site/index.html   gh gist
                                                        (Aladin Lite)
```

- `src/skydiff/fetch_alerce.py` — query ALeRCE stamp-classifier SN candidates (single `_get()` call site, 3 retries, 15 s timeout); per-object `magstats` supplies latest magnitude (g band preferred, r fallback); normalize to source-agnostic `Event`.
- `src/skydiff/store.py` — append `data/snapshots/date=YYYY-MM-DD/events.parquet` (same-day re-run overwrites).
- `src/skydiff/diff.py` — DuckDB anti-join (today vs **all** prior partitions) → additions; |Δmag| ≥ 0.3 vs latest prior partition → modifications.
- `src/skydiff/render_cli.py`, `render_html.py`, `publish_gist.py` — three renders of the same `DiffResult`.

### Diff semantics

| Symbol | Meaning | Rule |
|--------|---------|------|
| `+` | addition | `object_id` in today's snapshot, absent from all prior snapshots |
| `~` | modification | seen before, and \|mag_today − mag_prev\| ≥ 0.3 |
| (none) | unchanged | never printed |

### Window semantics (resolved at Gate 1)

`--since yesterday` = rolling now − 24 h converted to MJD; `--since 2026-08-12` = that civil date at 00:00 UTC. ALeRCE filter is `firstmjd ≥ window start`.

### Event schema (source-agnostic)

`source, object_id, event_type, ra, dec, object_class, prob, mag, discovered_mjd, fetched_at, payload` — see `src/skydiff/schema.py`. Adding source #2 = one new `fetch_*.py` producing `Event` rows; store/diff/render untouched.

## Tests

```bash
uv run pytest        # 9 tests, fixtures only — never hits the live API
uv run ruff check src tests
```

Fixtures under `tests/fixtures/` were captured live at Gate 0 (2026-08-13): `day_n_*` is a real API response; `day_n1_*` is doctored (+1 new object, one object brightened 0.5 mag).

## Spike results (Gate log)

| Gate | Result |
|------|--------|
| 0 | live endpoint verified — note: `/objects` needs trailing slash + redirect follow; magnitude requires per-object `/objects/{oid}/magstats` |
| 1 | two Parquet partitions from real + doctored data |
| 2 | anti-join diff: expected `+`/`~` rows, unit-tested |
| 3 | CLI output matches RDD example |
| 4 | `site/index.html` opens from `file://`, markers at correct RA/Dec |
| 5 | `--publish` prints gist URL; `SKYDIFF_GIST_ID` updates in place (via `gh api PATCH` — `gh gist edit` is interactive-only) |

Real morning run, 2026-08-13 (last 24 h, P ≥ 0.5): 5 SN candidates.

## Open questions (spike findings)

- Probability threshold 0.5 → 5 candidates/24 h. Not noisy; could even lower to 0.4.
- Latest-mag delta ≥ 0.3: crude but produced sensible `~` lines. Keep for spike.
- Gist: update-in-place (journal-style) implemented and verified.

## Non-goals (spike)

Multiple sources, scheduling, location filtering, light curves, any hosted service.
