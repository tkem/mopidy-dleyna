Installation
========================================================================

On Debian Linux and Debian-based distributions like Ubuntu or
Raspbian, install the ``mopidy-dleyna`` package from apt.mopidy.com_::

  apt-get install mopidy-dleyna

Otherwise, first make sure the following dependencies are met on your
system:

- D-Bus Python bindings, such as the package ``python-dbus`` in
  Debian/Ubuntu/Raspbian.

- The ``dbus-launch`` command, available in the ``dbus-x11`` package
  on Debian and Ubuntu.

- The ``dleyna-server`` package available in Ubuntu 14.04 and Debian
  "jessie".  For other platforms, please see the dLeyna `installation
  instructions <https://github.com/01org/dleyna-server>`_.

Then install the Python package from PyPI_::

  pip install Mopidy-dLeyna


.. _apt.mopidy.com: http://apt.mopidy.com/
.. _PyPI: https://pypi.python.org/pypi/Mopidy-dLeyna/
