# Mopidy-dLeyna

Mopidy backend extension for browsing, searching and playing media from DLNA Digital
Media Servers through the dLeyna D-Bus service. Pure Python ≥ 3.13, `src/` layout, no
annotations; depends on Mopidy ≥ 4, Pykka, `uritools` and `dbus-python`, which is a
system package checked by `Extension.validate_environment()`, not a declared
dependency. Single maintainer; `master` is the release branch and `develop` the
integration branch that PRs and Dependabot target. Code reviews follow
`.github/copilot-instructions.md`.

## Commands

Run everything through `tox`, never bare `pytest`, `ruff` or `pyright`:

```bash
tox -p auto                                  # default environments, as CI does
tox -e py -- tests/test_browse.py -k root    # tests; posargs go to pytest
tox -e ruff,ruff-format,docs                 # lint, format, docs
tox -e pyright                               # not in envlist yet: still fails
```

Installing Mopidy builds PyGObject, which needs the GObject introspection and cairo
headers (`libgirepository-2.0-dev`, `libcairo2-dev`, `pkg-config` on Debian/Ubuntu).
CI (GitHub Actions on `tkem/mopidy-dleyna`, every push) runs CPython 3.13 and 3.14
inside the `ghcr.io/mopidy/ci` container; without `gh`, check runs via
`https://api.github.com/repos/tkem/mopidy-dleyna/actions/runs?branch=<branch>`.
Coverage is reported to Codecov and is not complete; see `.github/copilot-review.md`.
`python -m mopidy_dleyna.client` queries a running dLeyna server for manual checks.

## Code Style

- `ruff check` and `ruff format` with the default rules; `[tool.ruff.lint]` in
  `pyproject.toml` ignores `BLE001` (D-Bus errors are caught broadly on purpose),
  `RUF012` (Mopidy's class attributes) and `UP031`. Do not add `noqa` comments; the
  one on the `dbus` import in `validate_environment()` is the only exception.
- No type annotations in `src/`; keep the code compatible with pyright's
  `standard` mode where it is cheap to do so.
- Private state uses double-underscore names (`self.__servers`); all D-Bus calls go
  through `dLeynaClient`, which returns `util.Future` objects, never raw replies.
- Log with `logger.error("... %s", arg)`, never f-strings, and never raise from
  `browse()`, `lookup()`, `get_images()`, `search()` or `translate_uri()`: Mopidy
  clients expect an empty result. Skip and log objects of unsupported types
  (`ValueError` from the translator) instead of failing a listing.
- Docs (`docs/index.rst`): wrap prose at column 70, two spaces after a sentence,
  `confval` entries for every setting in `ext.conf`. Keep `README.rst` in sync.

## Architecture Constraints

- URIs are `dleyna:` (root), `dleyna://<UDN>` for media servers and
  `dleyna://<UDN>/<path>` for objects, where the path is the D-Bus object path
  below the server's; `client.urimapper()` and `__parseuri()` convert between them.
  Saved playlists depend on them; keep the mapping stable.
- `Servers` tracks media servers from dLeyna's `FoundServer`/`LostServer` signals,
  keyed by lower-case UDN and guarded by a lock, since signals arrive on the D-Bus
  main loop thread.
- All client calls are asynchronous: `util.Future.fromdbus()` wraps reply and error
  handlers, and `library.iterate()` pages through Browse and Search results by
  `upnp_*_limit`, blocking only when the results are consumed.
- Search and multi-object lookup depend on each server's `SearchCaps`;
  `translator.query()` raises `NotImplementedError` for unsupported keywords, and
  `search()` returns `None` if no server can search. Sorting follows `SortCaps`.
- The backend starts its own D-Bus session bus with `dbus_start_session` if none is
  found, and stops it in `on_stop()`.
- Configuration keys live in `ext.conf` and `Extension.get_config_schema()`; both
  must change together, as must the test `config` fixture.

## Testing

- New behavior needs tests under `tests/`; user-visible changes need docs in
  `docs/index.rst`. Tests never touch D-Bus: the library and playback providers
  get a mock `backend` whose `client` returns `util.Future.fromvalue()` results.
- Translator tests feed raw dLeyna property dicts and compare against Mopidy models.

## Boundaries

- Never edit `CHANGELOG.rst` or bump `__version__`; both are release-only.
- Never change URIs or configuration keys without a deprecation path.
- Do not re-raise the *Maintainer Decisions* in `.github/copilot-instructions.md`.

## Git

- PRs target `develop` and reference an open issue (except trivial fixes), in
  separate commits:
  `Fix #123: ...`, `Tests for #123: ...`, `Docs for #123: ...`.
- Run `tox -p auto` before pushing. Update this file in the same PR that changes a
  convention, and keep it under 100 lines.
