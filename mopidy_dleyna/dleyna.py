from __future__ import absolute_import, unicode_literals

import logging
import sys
import threading
import time

import dbus

import pykka


MEDIA_CONTAINER_IFACE = 'org.gnome.UPnP.MediaContainer2'

MEDIA_DEVICE_IFACE = 'com.intel.dLeynaServer.MediaDevice'

MEDIA_ITEM_IFACE = 'org.gnome.UPnP.MediaItem2'

SERVER_BUS_NAME = 'com.intel.dleyna-server'

SERVER_MANAGER_IFACE = 'com.intel.dLeynaServer.Manager'

SERVER_ROOT_PATH = '/com/intel/dLeynaServer'

logger = logging.getLogger(__name__)


def _future(value):
    future = pykka.Future()
    future.set_get_hook(lambda timeout: value)
    return future


def _exc_future(exc_info):
    future = pykka.ThreadingFuture()
    future.set_exception(exc_info=exc_info)
    return future


def _dbus_future(func, *args, **kwargs):
    # TODO: remove timing info
    future = pykka.ThreadingFuture()
    t = time.time()

    def on_reply(result):
        logger.info('%s reply after %.3fs', func, time.time() - t)
        future.set(result)

    def on_error(e):
        logger.info('%s error after %.3fs', func, time.time() - t)
        future.set_exception(exc_info=(type(e), e, None))

    func(*args, reply_handler=on_reply, error_handler=on_error, **kwargs)
    return future


class dLeynaClient(object):

    def __init__(self, address=None, mainloop=None):
        if address:
            bus = dbus.bus.BusConnection(address, mainloop=mainloop)
        else:
            bus = dbus.SessionBus(mainloop=mainloop)
        self.__bus = bus
        self.__bypath = {}
        self.__byudn = {}
        self.__lock = threading.RLock()

        def reply_handler(paths):
            for path in paths:
                self.__found_server(path)

        def error_handler(e):
            logger.info('Error retrieving DLNA servers: %s', e)

        bus.add_signal_receiver(
            self.__found_server, 'FoundServer',
            bus_name=SERVER_BUS_NAME
        )
        bus.add_signal_receiver(
            self.__lost_server, 'LostServer',
            bus_name=SERVER_BUS_NAME
        )
        bus.get_object(SERVER_BUS_NAME, SERVER_ROOT_PATH).GetServers(
            dbus_interface=SERVER_MANAGER_IFACE,
            reply_handler=reply_handler,
            error_handler=error_handler
        )

    def children(self, path, offset=0, limit=0, filter=['*']):
        return _dbus_future(
            self.__bus.get_object(SERVER_BUS_NAME, path).ListChildren,
            dbus.UInt32(offset), dbus.UInt32(limit), filter,
            dbus_interface=MEDIA_CONTAINER_IFACE
        )

    def properties(self, path, iface=''):
        return _dbus_future(
            self.__bus.get_object(SERVER_BUS_NAME, path).GetAll,
            iface, dbus_interface=dbus.PROPERTIES_IFACE
        )

    def rescan(self):
        return _dbus_future(
            self.__bus.get_object(SERVER_BUS_NAME, SERVER_ROOT_PATH).Rescan,
            dbus_interface=SERVER_MANAGER_IFACE
        )

    def search(self, path, query, offset=0, limit=0, filter=['*']):
        return _dbus_future(
            self.__bus.get_object(SERVER_BUS_NAME, path).SearchObjects,
            query, dbus.UInt32(offset), dbus.UInt32(limit), filter,
            dbus_interface=MEDIA_CONTAINER_IFACE
        )

    def server(self, udn):
        try:
            with self.__lock:
                return _future(self.__byudn[udn])
        except KeyError:
            e = LookupError('DLNA media server not found: %s' % udn)
            return _exc_future((type(e), e, sys.exc_info()[2]))

    def servers(self):
        with self.__lock:
            return _future(list(self.__bypath.values()))

    def __found_server(self, path):
        def reply_handler(properties):
            udn = properties['UDN']
            name = properties['FriendlyName']
            logger.info('Found DLNA media server %s [%s]', name, udn)
            with self.__lock:
                self.__bypath[path] = self.__byudn[udn] = properties

        def error_handler(e):
            logger.error('Cannot access DLNA media server %s: %s', path, e)

        self.__bus.get_object(SERVER_BUS_NAME, path).GetAll(
            '',  # all interfaces
            dbus_interface=dbus.PROPERTIES_IFACE,
            reply_handler=reply_handler,
            error_handler=error_handler
        )

    def __lost_server(self, path):
        try:
            props = self.__bypath[path]
            name = props['FriendlyName']
            udn = props['UDN']
            with self.__lock:
                del self.__byudn[udn]
                del self.__bypath[path]
        except KeyError:
            logger.debug('Unknown DLNA server path %s', path)
        except Exception:
            logger.error('Error removing %s', path, exc_info=True)
        else:
            logger.info('Lost DLNA media server %s [%s]', name, udn)
