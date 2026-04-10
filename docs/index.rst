:tocdepth: 3

*************
Mopidy-dLeyna
*************

Mopidy-dLeyna is a Mopidy_ extension that lets you play music from
DLNA_ Digital Media Servers using the dLeyna_ D-Bus interface.

This extension lets you browse, search, and stream music from your
NAS, PC, or any other device running a UPnP/DLNA compliant media
server.  Compatible devices are discovered automatically on your local
network, so there is no configuration needed.

*************
Configuration
*************

This extension provides a number of configuration values that can be
tweaked.  However, the :ref:`default configuration <defconf>` should
contain everything to get you up and running, and will usually require
only a few modifications, if any, to match personal preferences.


.. _confvals:

Configuration Values
====================

.. confval:: enabled

   Whether this extension should be enabled or not.

.. confval:: upnp_browse_limit

   The maximum number of objects to retrieve per UPnP `Browse` action,
   or ``0`` to retrieve all objects.

.. confval:: upnp_lookup_limit

   The maximum number of objects to retrieve by ID in a single UPnP
   `Search` action, or ``0`` for no limit.  Note that for this setting
   to have any effect, the media server must advertise that it is
   capable of searching for object IDs.

   This is an *experimental* setting and may be changed or removed in
   future versions.

.. confval:: upnp_search_limit

   The maximum number of objects to retrieve per UPnP `Search` action,
   or ``0`` to retrieve all objects.

.. confval:: dbus_start_session

   The command to start a D-Bus session bus if none is found, for
   example when running Mopidy as a service.


.. _defconf:

Default Configuration
=====================

For reference, this is the default configuration shipped with
Mopidy-dLeyna release |release|:

.. literalinclude:: ../src/mopidy_dleyna/ext.conf
   :language: ini


.. _Mopidy: http://www.mopidy.com/
.. _DLNA: http://www.dlna.org/
.. _dLeyna: http://01.org/dleyna
