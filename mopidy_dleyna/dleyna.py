from __future__ import absolute_import, unicode_literals

import logging
import threading

import dbus

MEDIA_CONTAINER_IFACE = 'org.gnome.UPnP.MediaContainer2'

MEDIA_ITEM_IFACE = 'org.gnome.UPnP.MediaItem2'

SERVER_BUS_NAME = 'com.intel.dleyna-server'

SERVER_MANAGER_IFACE = 'com.intel.dLeynaServer.Manager'

SERVER_ROOT_PATH = '/com/intel/dLeynaServer'

logger = logging.getLogger(__name__)


class dLeynaClient(object):

    def __init__(self):
        self.__bus = bus = dbus.SessionBus()
        self.__lock = threading.RLock()
        self.__bypath = {}
        self.__byudn = {}

        self.__manager = self.get_object(
            SERVER_ROOT_PATH,
            SERVER_MANAGER_IFACE
        )
        bus.add_signal_receiver(
            self.add_server,
            bus_name=SERVER_BUS_NAME,
            signal_name='FoundServer'
        )
        bus.add_signal_receiver(
            self.remove_server,
            bus_name=SERVER_BUS_NAME,
            signal_name='LostServer'
        )
        for path in self.__manager.GetServers():
            self.add_server(path)

    def get_object(self, path, iface=None):
        obj = self.__bus.get_object(SERVER_BUS_NAME, path)
        return dbus.Interface(obj, iface) if iface else obj

    def get_properties(self, path):
        return self.get_object(path, dbus.PROPERTIES_IFACE).GetAll('')

    def get_server(self, udn):
        try:
            with self.__lock:
                return self.__byudn[udn]
        except KeyError:
            raise LookupError('DLNA media server not found: %s' % udn)

    def get_container(self, path):
        return self.get_object(path, MEDIA_CONTAINER_IFACE)

    def get_item_url(self, path):
        obj = self.__bus.get_object(SERVER_BUS_NAME, path)
        props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
        urls = props.Get(MEDIA_ITEM_IFACE, 'URLs')
        return urls[0]

    def servers(self):
        with self.__lock:
            return list(self.__bypath.values())

    def add_server(self, path):
        props = self.get_properties(path)
        udn = props['UDN']
        with self.__lock:
            self.__bypath[path] = props
            self.__byudn[props['UDN']] = props
        logger.info('Added DLNA media server %s', udn)

    def remove_server(self, path):
        try:
            with self.__lock:
                udn = self.__bypath[path]['UDN']
                del self.__bypath[path]
                del self.__byudn[udn]
            logger.info('Removed DLNA media server %s', udn)
        except KeyError:
            logger.error('Unknown DLNA server path %s', path)

    def rescan(self):
        self.__manager.Rescan()
