v2.0.2 (2022-04-03)
===================

- Support Python 3.10.


v2.0.1 (2020-07-06)
===================

- Add ``DisplayName`` fallback for Plex media server.


v2.0.0 (2019-12-25)
===================

- Depend on final release of Mopidy 3.0.0.


v2.0.0a1 (2019-12-05)
=====================

- Require Python >= 3.7. (PR: #66)

- Require Mopidy >= 3.0.0a5. (PR: #66)

- Require Pykka >= 2.0.1. (PR: #66)

- Update project setup. (PR: #66)


v1.2.2 (2018-05-08)
===================

- Add workaround for browsing errors with certain media servers.


v1.2.1 (2017-10-24)
===================

- Add support for ``audioBook``, ``audioBroadcast`` and
  ``playlistContainer`` classes.

- Improve handling of browse and search limits.


v1.2.0 (2016-09-23)
===================

- Add ``dbus_start_session`` configuration value for specifying the
  command to start a session bus.  The default is to invoke
  ``dbus-daemon`` directly, so ``dbus-launch`` is no longer needed
  (but is still supported for now).

- Check for ``$XDG_RUNTIME_DIR/bus`` before starting a session bus.

- Update installation dependencies.

- Improve log messages if search is not supported.


v1.1.1 (2016-06-28)
===================

- Add workaround for partially retrieved browse results with Kodi
  16.0 DLNA server.


v1.1.0 (2016-05-21)
===================

- Add ``upnp_lookup_limit`` configuration value (experimental).

- Add support for ``albumartist`` queries.

- Add support for minidlna "All Albums" collections.

- Add track bitrate according to DLNA specification.

- Add basic unit tests for ``library`` and ``playback`` providers.

- Update documentation and build environment.

- Various code refactorings and improvements.


v1.0.5 (2016-01-22)
===================

- Specify sort order when browsing.

- Add ``apt.mopidy.com`` to installation options.

- Remove ``Album.images`` property (deprecated in Mopidy v1.2).

- Handle exceptions in ``dLeynaPlaybackProvider``.


v1.0.4 (2015-11-03)
===================

- Handle uppercase characters in server UDNs.


v1.0.3 (2015-10-24)
===================

- Refactor server handling.

- Handle persistent URIs in ``dLeynaClient``.


v1.0.2 (2015-10-16)
===================

- Improve startup error messages.

- Performance improvements.


v1.0.1 (2015-09-12)
===================

- Add workaround for permanently lost media servers.


v1.0.0 (2015-08-21)
===================

- Add ``upnp_browse_limit`` config value.

- Add ``upnp_search_limit`` config value.

- Refactor ``get_images`` implementation.

- Improve debug output.


v0.5.3 (2015-08-19)
===================

- Fix lost server handling.

- Check device's `SearchCaps` when searching.

- Improve log messages.


v0.5.2 (2015-08-18)
===================

- Move mapping helpers to translator module.

- Add ``mopidy_dleyna.dleyna.__main__``.

- Update `README.rst`.


v0.5.1 (2015-08-14)
===================

- Start/stop D-Bus daemon from backend.


v0.5.0 (2015-08-14)
===================

- Add support for album art.


v0.4.2 (2015-08-14)
===================

- Use asynchronous D-Bus calls to improve performance on Raspberry Pi.


v0.4.1 (2015-08-11)
===================

- Add workaround for integer conversion issues on 32 bit systems.


v0.4.0 (2015-08-11)
===================

- Start session bus on headless systems or when running as a daemon.

- Use recursive search for container lookups.

- Add browse/search filters.

- Persistent URI handling.


v0.3.1 (2015-04-11)
===================

- Perform search asynchronously.


v0.3.0 (2015-04-10)
===================

- Add basic search capabilities.

- Return proper reference types when browsing.


v0.2.0 (2015-04-08)
===================

- Add workaround for `minidlna` crashing on empty filter.


v0.1.0 (2015-04-07)
===================

- Initial release.
