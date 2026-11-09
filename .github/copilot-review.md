# Code Review — Mopidy-dLeyna 3.0.0

**Date:** 2026-11-09
**Reviewed:** `develop` at `6297915` ("Tests for client errors in library provider
methods."), i.e. v3.0.0 plus the build environment update and the fix for client
errors in the library provider.

**CI status:** All default `tox` environments pass locally on CPython 3.13.18 (`py`:
41 passed) with Mopidy 4.0.5; not run on 3.14 locally and not against a real dLeyna
server. GitHub Actions passed on 3.13 and 3.14 for the merged PRs; its run for this
commit had not finished when this review was written. `tox -e pyright` fails with
56 errors (Code #3). **Coverage:** 50 % with branches; `translator.py` and
`playback.py` are at 100 %, `library.py` at 92 %, but `backend.py` and `client.py`
(0 %) and `util.py` (60 %) are never exercised, since all tests use a mock client.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `backend.py` `__stop_session_bus` | The regular shutdown of the extension's own D-Bus daemon is logged with `logger.error` ("Stopping ... D-Bus daemon"). |
| 2 | Low | `client.py` `urimapper` | Object paths outside the server prefix are rejected with `assert`, which `python -O` strips, so a bad path would silently map to a wrong URI. |
| 3 | Low | whole package, `tests/` | pyright `standard` reports 56 errors: Mopidy 4's typed models (`Uri`, `ReleaseDate`, `DurationMs`, `tuple` artists and search results) reject plain values, `self.backend.client` is unknown on `backend.Backend`, `root_directory.uri` is optional, and `dbus` cannot be resolved in the tox environment. Blocks adding `pyright` to the envlist. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `dLeynaBackend` (session bus detection, start and stop), `dLeynaClient` (URI mapping, `SortCaps` filtering, `Servers` signals) and `util.Future.fromdbus()` have no tests. |
| 2 | Low | `iterate()` ending a listing on an error after the first page (line 52) is untested; `tests/test_errors.py` covers errors on the first page only. |
| 3 | Info | Two `DeprecationWarning`s come from `mopidy.types` at import time, not from this package. |

## Changelog

| # | Priority | Finding |
|---|----------|---------|
| 1 | Medium | The next release's entry needs a line for the changed behavior, e.g. "Log errors and return empty results from ``browse()``, ``lookup()``, ``get_images()`` and ``search()`` instead of raising.", plus "Update build environment." for the ruff, `tox` and CI changes and the removal of `setup.cfg` and `setup.py`. |
