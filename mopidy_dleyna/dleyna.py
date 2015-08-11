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
        self.__bus = bus = self.__session_bus()
        self.__lock = threading.RLock()
        self.__bypath = {}
        self.__byudn = {}
        self.__manager = mgr = self.get_object(
            SERVER_ROOT_PATH,
            SERVER_MANAGER_IFACE
        )
        logger.debug('dleyna-server version %s', mgr.GetVersion())
        bus.add_signal_receiver(
            self.found_server, 'FoundServer',
            bus_name=SERVER_BUS_NAME
        )
        bus.add_signal_receiver(
            self.lost_server, 'LostServer',
            bus_name=SERVER_BUS_NAME
        )
        # TODO: delay until later?
        for path in mgr.GetServers():
            self.found_server(path)

    def get_object(self, path, iface=None):
        obj = self.__bus.get_object(SERVER_BUS_NAME, path)
        return dbus.Interface(obj, iface) if iface else obj

    def get_properties(self, path):
        return self.get_object(path, dbus.PROPERTIES_IFACE).GetAll('')

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

    def get_server(self, udn):
        try:
            with self.__lock:
                return self.__byudn[udn]
        except KeyError:
            raise LookupError('DLNA media server not found: %s' % udn)

    def found_server(self, path):
        try:
            props = self.get_properties(path)
            with self.__lock:
                self.__bypath[path] = self.__byudn[props['UDN']] = props
        except dbus.DBusException as e:
            logger.warn('Skipping %s: %s', path, e.get_dbus_message())
        except Exception:
            logger.error('Error adding %s', path, exc_info=True)
        else:
            logger.info('Found DLNA media server %s [%s]',
                        props['FriendlyName'], props['UDN'])

    def lost_server(self, path):
        try:
            props = self.__bypath[path]
            with self.__lock:
                del self.__byudn[props['UDN']]
                del self.__bypath[path]
        except KeyError:
            logger.debug('Unknown DLNA server path %s', path)
        except Exception:
            logger.error('Error removing %s', path, exc_info=True)
        else:
            logger.info('Lost DLNA media server %s [%s]',
                        props['FriendlyName'], props['UDN'])

    def rescan(self):
        self.__manager.Rescan()

    def __session_bus(self):
        import os
        # FIXME: dbus.SessionBus() ignores DBUS_SESSION_BUS_ADDRESS?
        return dbus.bus.BusConnection(os.environ['DBUS_SESSION_BUS_ADDRESS'])
