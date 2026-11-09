# Code Review — Mopidy-dLeyna 3.0.0

**Date:** 2026-11-09
**Reviewed:** branch `build-environment` (two commits: "Update build environment and
add AGENTS.md." and "Configure ruff and pyright, apply ruff fixes."), based on
`develop` at `6ab23ef` ("Bump actions/setup-python from 6.2.0 to 6.3.0"), i.e.
v3.0.0 plus dependency bumps.

**CI status:** All default `tox` environments pass locally on CPython 3.13.18 (`py`:
25 passed) with Mopidy 4.0.5; not run on 3.14 and not against a real dLeyna server.
`tox -e pyright` fails with 56 errors (Code #5). GitHub Actions has not run for
this branch. **Coverage:** 47 % with branches; `translator.py` and `playback.py`
are at 100 %, `library.py` at 88 %, but `backend.py` and `client.py` (0 %) and
`util.py` (60 %) are never exercised, since all tests use a mock client.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Medium | `library.py` `browse`, `lookup`, `get_images`, `search` | Client errors are not caught: an unknown media server (`LookupError` from the client, e.g. after the server went offline) and D-Bus errors propagate to Mopidy; `get_images()` and `search()` only catch `NotImplementedError`. Probed with the mock client's futures raising. |
| 2 | Low | `library.py` `__browse` | Browsing a track URI raises `KeyError` because `BROWSE_ORDER` has no entry for `Ref.TRACK`, instead of returning `[]`. |
| 3 | Low | `backend.py` `__stop_session_bus` | The regular shutdown of the extension's own D-Bus daemon is logged with `logger.error` ("Stopping ... D-Bus daemon"). |
| 4 | Low | `client.py` `urimapper` | Object paths outside the server prefix are rejected with `assert`, which `python -O` strips, so a bad path would silently map to a wrong URI. |
| 5 | Low | whole package, `tests/` | pyright `standard` reports 56 errors: Mopidy 4's typed models (`Uri`, `ReleaseDate`, `DurationMs`, `tuple` artists and search results) reject plain values, `self.backend.client` is unknown on `backend.Backend`, `root_directory.uri` is optional, and `dbus` cannot be resolved in the tox environment. Blocks adding `pyright` to the envlist. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `dLeynaBackend` (session bus detection, start and stop), `dLeynaClient` (URI mapping, `SortCaps` filtering, `Servers` signals) and `util.Future.fromdbus()` have no tests. |
| 2 | Low | No test covers client errors in `browse()`, `lookup()`, `get_images()` or `search()` (Code #1, #2), nor `iterate()` stopping on an error after the first page (lines 48–55). |
| 3 | Info | Two `DeprecationWarning`s come from `mopidy.types` at import time, not from this package. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `README.rst` still shows a "code style: black" badge, although formatting is done with `ruff format`. |

## Changelog

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | The build changes on this branch (ruff configuration, `tox` and CI updates, removal of `setup.cfg` and `setup.py`) need an "Update build environment." line in the next release's entry. |
