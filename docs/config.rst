Configuration
========================================================================

This extension provides a number of configuration values that can be
tweaked.  However, the :ref:`default configuration <defconf>` should
contain everything to get you up and running, and will usually require
only a few modifications, if any, to match personal preferences.


.. _confvals:

Configuration Values
------------------------------------------------------------------------

.. confval:: dleyna/enabled

   Whether this extension should be enabled or not.

.. confval:: dleyna/upnp_browse_limit

   The maximum number of objects to retrieve per UPnP `Browse` action,
   or ``0`` to retrieve all objects.

.. confval:: dleyna/upnp_lookup_limit

   The maximum number of objects to retrieve by ID in a single UPnP
   `Search` action, or ``0`` for no limit.  Note that for this setting
   to have any effect, the media server must advertise that it is
   capable of searching for object IDs.

   This is an *experimental* setting and may be changed or removed in
   future versions.

.. confval:: dleyna/dleyna/upnp_search_limit

   The maximum number of objects to retrieve per UPnP `Search` action,
   or ``0`` to retrieve all objects.


.. _defconf:

Default Configuration
------------------------------------------------------------------------

For reference, this is the default configuration shipped with
Mopidy-dLeyna release |release|:

.. literalinclude:: ../mopidy_dleyna/ext.conf
   :language: ini
