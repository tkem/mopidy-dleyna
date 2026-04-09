*************
Mopidy-dLeyna
*************

.. image:: https://img.shields.io/pypi/v/Mopidy-dLeyna
    :target: https://pypi.org/project/Mopidy-dLeyna/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/github/actions/workflow/status/tkem/mopidy-dleyna/ci.yml
   :target: https://github.com/tkem/mopidy-dleyna/actions/workflows/ci.yml
   :alt: CI build status

.. image:: https://img.shields.io/readthedocs/mopidy-dleyna
    :target: https://mopidy-dleyna.readthedocs.io/
    :alt: Documentation build status

.. image:: https://img.shields.io/codecov/c/gh/tkem/mopidy-dleyna
    :target: https://codecov.io/gh/tkem/mopidy-dleyna
    :alt: Test coverage

.. image:: https://img.shields.io/github/license/tkem/mopidy-dleyna
   :target: https://raw.github.com/tkem/mopidy-dleyna/master/LICENSE
   :alt: License

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Code style: black

Mopidy-dLeyna is a Mopidy_ extension that lets you play music from
DLNA_ Digital Media Servers using the dLeyna_ D-Bus interface.

This extension lets you browse, search, and stream music from your
NAS, PC, or any other device running a UPnP/DLNA compliant media
server.  Compatible devices are discovered automatically on your local
network, so there is no configuration needed.


Installation
============

On Debian Linux and Debian-based distributions like Ubuntu or
Raspbian, install the ``mopidy-dleyna`` package from apt.mopidy.com_::

  apt-get install mopidy-dleyna

Otherwise, first make sure the following dependencies are met on your
system:

- D-Bus Python bindings, such as the package ``python-dbus`` in
  Debian/Ubuntu/Raspbian [#footnote1]_.

- The ``dleyna-server`` package available in Ubuntu 14.04 and Debian
  "jessie".  For other platforms, please see the dLeyna `installation
  instructions <https://github.com/01org/dleyna-server>`_.

Then install the Python package from PyPI_::

  pip install Mopidy-dLeyna

  
Project resources
=================

- `Documentation`_
- `Issue tracker`_
- `Source code`_
- `Change log`_


License
=======

Copyright (c) 2015-2026 Thomas Kemmer.

Licensed under the `Apache License, Version 2.0`_.


Credits
=======

- Original author: `Thomas Kemmer <https://github.com/tkem>`__
- Current maintainer: `Thomas Kemmer <https://github.com/tkem>`__
- `Contributors <https://github.com/tkem/mopidy-dleyna/graphs/contributors>`_


.. rubric:: Footnotes

.. [#footnote1] On some distributions such as Arch Linux, it may also
  be necessary to install the ``dbus-glib`` package.
  
.. _Mopidy: http://www.mopidy.com/
.. _DLNA: http://www.dlna.org/
.. _dLeyna: http://01.org/dleyna

.. _apt.mopidy.com: http://apt.mopidy.com/
.. _PyPI: https://pypi.python.org/pypi/Mopidy-dLeyna/

.. _Documentation: https://mopidy-dleyna.readthedocs.io/
.. _Source code: https://github.com/tkem/mopidy-dleyna
.. _Issue tracker: https://github.com/tkem/mopidy-dleyna/issues
.. _Change log: https://github.com/tkem/mopidy-dleyna/blob/master/CHANGELOG.rst

.. _Apache License, Version 2.0: https://raw.github.com/tkem/mopidy-dleyna/master/LICENSE
