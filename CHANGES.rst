1.0.0 2015-08-20
----------------

- Add ``upnp_browse_limit`` config value.

- Add ``upnp_search_limit`` config value.

- Refactor ``get_images`` implementation.

- Improve debug output.
  

0.5.3 2015-08-19
----------------

- Fix lost server handling.

- Check device's `SearchCaps` when searching.

- Improve log messages.


0.5.2 2015-08-18
----------------

- Move mapping helpers to translator module.

- Add ``mopidy_dleyna.dleyna.__main__``.

- Update `README.rst`.


0.5.1 2015-08-14
----------------

- Start/stop D-Bus daemon from backend.


0.5.0 2015-08-14
----------------

- Add support for album art.


0.4.2 2015-08-14
----------------

- Use asynchronous D-Bus calls to improve performance on Raspberry Pi.


0.4.1 2015-08-11
----------------

- Add workaround for integer conversion issues on 32 bit systems.


0.4.0 2015-08-11
----------------

- Start session bus on headless systems or when running as a daemon.

- Use recursive search for container lookups.

- Add browse/search filters.

- Peristent URI handling.


0.3.1 2015-04-11
----------------

- Perform search asynchronously.


0.3.0 2015-04-10
----------------

- Add basic search capabilities.

- Return proper reference types when browsing.


0.2.0 2015-04-08
----------------

- Add workaround for `minidlna` crashing on empty filter.


0.1.0 2015-04-07
----------------

- Initial release.
