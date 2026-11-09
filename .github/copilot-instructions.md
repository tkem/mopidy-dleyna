# Copilot Instructions for Mopidy-dLeyna

Project conventions (stack, commands, code style, architecture constraints, boundaries
and git workflow) live in [`AGENTS.md`](../AGENTS.md). This file adds only the code
review process.

## Code Review

- Reviews **amend `.github/copilot-review.md` in place** (header: date, commit, CI
  status, coverage); never new files, dated sections, a per-commit change summary or
  a list of what was verified (git history is the record).
- Findings are tables ordered High, Medium, Low, Info with columns
  `# | Priority | Location | Finding`; renumber after changes; cross-reference as
  "Code #3". **Resolved issues are removed**, never marked resolved.
- Name the reviewed commit by hash and subject plus its base branch; after a rebase
  replace stale hashes instead of narrating history. List only interpreter versions
  actually run.
- Keep it brief: under 100 lines, one or two sentences per row, numbers only where
  they decide something, current snapshot only (no comparisons with earlier releases).
  Drop "no issues" sections and Info rows that only restate accepted design. Record
  settled matters under *Maintainer Decisions*. A review changes nothing; fix only
  when asked.
- `CHANGELOG.rst` is reviewed, never edited: entries are imperative one-liners with
  ``double backticks`` and no issue numbers, tagged "(breaking change)", "(potentially
  breaking change)" or "(broken since vX.Y.Z)". Every `Fix #123` commit and every
  user-visible behavior change needs an entry; docs-only, test-only and build work
  is one "Minor/Various ... improvements." or "Update build environment." line each;
  two blank lines between releases.
- Verify before reporting: probe behavior with scripts against a real
  `dLeynaLibraryProvider` with a mocked `dLeynaClient`. Media servers differ in their
  capabilities; findings about a real server must name the device they rest on.
- Whatever could not be verified must show up: mark the finding, figure or status as
  unverified where it stands (e.g. "not run on 3.14", "CI not run for this commit")
  and say why. Never state an unchecked claim as fact or leave it out.

## Maintainer Decisions (do not re-raise)

- D-Bus errors from media servers are caught broadly (`BLE001` is ignored): servers
  that fail when paging beyond the last item end a listing instead of failing it.
- `dbus-python` is not a declared dependency, since it is installed with the system
  D-Bus libraries; `validate_environment()` reports it missing.
- Known limitations, such as dLeyna not passing `TotalMatches` from Browse or date
  searches, are documented by `TODO` comments in the code.
- The code carries no type annotations; pyright runs in `standard` mode and is not
  part of the default `tox` envlist until its errors are fixed.
- CI runs inside `ghcr.io/mopidy/ci`, since Mopidy depends on PyGObject; free-threaded
  and PyPy builds are not tested.
