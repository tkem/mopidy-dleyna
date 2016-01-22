Mopidy-dLeyna
========================================================================

Mopidy-dLeyna is a Mopidy_ extension that lets you play music from
DLNA_ Digital Media Servers using the dLeyna_ D-Bus interface.


Dependencies
------------------------------------------------------------------------

- D-Bus Python bindings, such as the package ``python-dbus`` in
  Debian/Ubuntu/Raspbian.

- The ``dleyna-server`` package available in Ubuntu 14.04 and Debian
  "jessie".  For other platforms, please see the dLeyna `installation
  instructions <https://github.com/01org/dleyna-server>`_.


Installation
------------------------------------------------------------------------

Debian/Ubuntu/Raspbian: Install the ``mopidy-dleyna`` package from
`apt.mopidy.com <http://apt.mopidy.com/>`_::

  sudo apt-get install mopidy-dleyna

Otherwise, install the dependencies listed above, and then install the
package from PyPI_::

  pip install Mopidy-dLeyna


Configuration
------------------------------------------------------------------------

The following configuration values are provided:

- ``dleyna/enabled``: Whether this extension should be enabled or not.
  Defaults to ``true``

- ``dleyna/upnp_browse_limit``: The maximum number of objects to
  retrieve per UPnP `Browse` action, or ``0`` to retrieve all objects.
  Defaults to ``1000``.

- ``dleyna/upnp_search_limit``: The maximum number of objects to
  retrieve per UPnP `Search` action, or ``0`` to retrieve all objects.
  Defaults to ``0``.


Project resources
------------------------------------------------------------------------

.. image:: https://img.shields.io/pypi/v/Mopidy-dLeyna.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-dLeyna/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/Mopidy-dLeyna.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-dLeyna/
    :alt: Number of PyPI downloads

.. image:: https://img.shields.io/travis/tkem/mopidy-dleyna/master.svg?style=flat
    :target: https://travis-ci.org/tkem/mopidy-dleyna
    :alt: Travis CI build status

.. image:: https://img.shields.io/coveralls/tkem/mopidy-dleyna/master.svg?style=flat
   :target: https://coveralls.io/r/tkem/mopidy-dleyna?branch=master
   :alt: Test coverage

- `Issue Tracker`_
- `Source Code`_
- `Change Log`_


License
------------------------------------------------------------------------

Copyright (c) 2015, 2016 Thomas Kemmer.

Licensed under the `Apache License, Version 2.0`_.


.. _Mopidy: http://www.mopidy.com/
.. _DLNA: http://www.dlna.org/
.. _dLeyna: http://01.org/dleyna

.. _PyPI: https://pypi.python.org/pypi/Mopidy-dLeyna/
.. _Issue Tracker: https://github.com/tkem/mopidy-dleyna/issues/
.. _Source Code: https://github.com/tkem/mopidy-dleyna/
.. _Change Log: https://github.com/tkem/mopidy-dleyna/blob/master/CHANGES.rst

.. _Apache License, Version 2.0: http://www.apache.org/licenses/LICENSE-2.0
