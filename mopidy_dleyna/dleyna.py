from __future__ import absolute_import, unicode_literals

import logging
import threading
import time

import dbus

import pykka

SERVER_BUS_NAME = 'com.intel.dleyna-server'

SERVER_ROOT_PATH = '/com/intel/dLeynaServer'

SERVER_MANAGER_IFACE = 'com.intel.dLeynaServer.Manager'

logger = logging.getLogger(__name__)


class dLeynaClient(object):

    MEDIA_CONTAINER_IFACE = 'org.gnome.UPnP.MediaContainer2'

    MEDIA_DEVICE_IFACE = 'com.intel.dLeynaServer.MediaDevice'

    MEDIA_ITEM_IFACE = 'org.gnome.UPnP.MediaItem2'

    class Future(pykka.ThreadingFuture):

        def apply(self, func):
            # similar to map(), but always works on single value
            future = self.__class__()
            future.set_get_hook(lambda timeout: func(self.get(timeout)))
            return future

    def __init__(self, address=None, mainloop=None):
        if address:
            self.__bus = dbus.bus.BusConnection(address, mainloop=mainloop)
        else:
            self.__bus = dbus.SessionBus(mainloop=mainloop)
        self.__lock = threading.RLock()
        self.__servers = {}
        self.__bus.add_signal_receiver(
            self.__found_server, 'FoundServer',
            bus_name=SERVER_BUS_NAME
        )
        self.__bus.add_signal_receiver(
            self.__lost_server, 'LostServer',
            bus_name=SERVER_BUS_NAME
        )
        self.__future = self.__get_servers()  # TODO: rename

    def browse(self, path, offset=0, limit=0, filter=['*']):
        return self.__call_async(
            self.__bus.get_object(SERVER_BUS_NAME, path).ListChildren,
            dbus.UInt32(offset), dbus.UInt32(limit), filter,
            dbus_interface=self.MEDIA_CONTAINER_IFACE
        )

    def properties(self, path, iface=None):
        return self.__call_async(
            self.__bus.get_object(SERVER_BUS_NAME, path).GetAll,
            iface or '',
            dbus_interface=dbus.PROPERTIES_IFACE
        )

    def rescan(self):
        future = self.__call_async(
            self.__bus.get_object(SERVER_BUS_NAME, SERVER_ROOT_PATH).Rescan,
            dbus_interface=SERVER_MANAGER_IFACE
        )
        self.__future = self.__get_servers()  # TODO: rename
        return future

    def search(self, path, query, offset=0, limit=0, filter=['*']):
        return self.__call_async(
            self.__bus.get_object(SERVER_BUS_NAME, path).SearchObjects,
            query, dbus.UInt32(offset), dbus.UInt32(limit), filter,
            dbus_interface=self.MEDIA_CONTAINER_IFACE
        )

    def server(self, udn):
        def getter(servers):
            try:
                with self.__lock:
                    return servers[udn]
            except KeyError:
                raise LookupError('Media server not found: %s' % udn)
        return self.__future.apply(getter)

    def servers(self):
        def values(servers):
            with self.__lock:
                return list(servers.values())
        return self.__future.apply(values)

    def __found_server(self, path, notify_handler=lambda path, obj: None):
        def reply_handler(obj):
            udn = obj['UDN']
            with self.__lock:
                if udn not in self.__servers:
                    self.__log_server_action('Found', obj)
                self.__servers[udn] = obj  # always update
            notify_handler(path, obj)

        def error_handler(e):
            logger.warn('Cannot access media server %s: %s', path, e)
            notify_handler(path, e)

        self.__bus.get_object(SERVER_BUS_NAME, path).GetAll(
            '',  # all interfaces
            dbus_interface=dbus.PROPERTIES_IFACE,
            reply_handler=reply_handler,
            error_handler=error_handler
        )

    def __lost_server(self, path):
        with self.__lock:
            for udn, obj in list(self.__servers.items()):
                if obj['Path'] == path:
                    self.__log_server_action('Lost', obj)
                    del self.__servers[udn]

    def __get_servers(self):
        future = self.Future()

        def reply_handler(paths):
            logger.info('Found %d digital media server(s)', len(paths))
            if paths:
                pending = set(paths)

                def pending_handler(path, obj):
                    pending.remove(path)
                    if not pending:
                        future.set(self.__servers)
                for path in paths:
                    self.__found_server(path, pending_handler)
            else:
                future.set(self.__servers)

        def error_handler(e):
            logger.error('Cannot retrieve media servers: %s', e)
            future.set(self.__servers)

        self.__bus.get_object(SERVER_BUS_NAME, SERVER_ROOT_PATH).GetServers(
            dbus_interface=SERVER_MANAGER_IFACE,
            reply_handler=reply_handler,
            error_handler=error_handler
        )
        return future

    @classmethod
    def __call_async(cls, func, *args, **kwargs):
        method = getattr(func, '_method_name', '<unknown>')
        logger.debug('Calling D-Bus method %s%s', method, args)
        future = cls.Future()
        t = time.time()

        def reply_handler(value=None):
            logger.debug('%s reply after %.3fs', method, time.time() - t)
            future.set(value)

        def error_handler(e):
            logger.debug('%s error after %.3fs', method, time.time() - t)
            future.set_exception(exc_info=(type(e), e, None))

        func(
            *args,
            reply_handler=reply_handler,
            error_handler=error_handler,
            **kwargs
        )
        return future

    @classmethod
    def __log_server_action(cls, action, obj):
        logger.info(
            '%s media server %s: %s [%s]',
            action, obj['Path'], obj['FriendlyName'], obj['UDN']
        )

if __name__ == '__main__':
    import argparse
    import json
    import sys

    import dbus.mainloop.glib
    import gobject

    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='?')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-f', '--filter', default='*')
    parser.add_argument('-i', '--indent', type=int, default=2)
    parser.add_argument('-l', '--list', action='store_true')
    parser.add_argument('-q', '--query')

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.ERROR)
    client = dLeynaClient(mainloop=dbus.mainloop.glib.DBusGMainLoop())
    filter = args.filter.split(',')

    if not args.path:
        future = client.servers()
    elif args.list:
        future = client.browse(args.path, filter=filter)
    elif args.query:
        future = client.search(args.path, args.query, filter=filter)
    else:
        future = client.properties(args.path)

    while True:
        try:
            future.get(timeout=0)
        except pykka.Timeout:
            gobject.MainLoop().get_context().iteration(True)
        else:
            break

    json.dump(future.get(), sys.stdout, default=vars, indent=args.indent)
    sys.stdout.write('\n')
