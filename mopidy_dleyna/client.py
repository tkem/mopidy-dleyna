from __future__ import absolute_import, unicode_literals

import collections
import logging
import threading
import time

import dbus

import pykka

import uritools

from . import translator

SERVER_BUS_NAME = 'com.intel.dleyna-server'

SERVER_ROOT_PATH = '/com/intel/dLeynaServer'

SERVER_MANAGER_IFACE = 'com.intel.dLeynaServer.Manager'

logger = logging.getLogger(__name__)


class dLeynaFuture(pykka.ThreadingFuture):
    def apply(self, func):
        # similar to map(), but always works on single value
        future = self.__class__()
        future.set_get_hook(lambda timeout: func(self.get(timeout)))
        return future

    @classmethod
    def fromdbus(cls, func, *args, **kwargs):
        method = getattr(func, '_method_name', '<unknown>')
        logger.debug('Calling D-Bus method %s%s', method, args)
        future = cls()
        start = time.time()

        def reply(value=None):
            logger.debug('%s reply after %.3fs', method, time.time() - start)
            future.set(value)

        def error(e):
            logger.debug('%s error after %.3fs', method, time.time() - start)
            future.set_exception(exc_info=(type(e), e, None))

        func(*args, reply_handler=reply, error_handler=error, **kwargs)
        return future

    @classmethod
    def fromvalue(cls, value):
        future = cls()
        future.set(value)
        return future


class dLeynaServers(collections.Mapping):

    def __init__(self, bus):
        self.__bus = bus
        self.__lock = threading.RLock()
        self.__servers = {}

        bus.add_signal_receiver(
            self.__found_server, 'FoundServer',
            bus_name=SERVER_BUS_NAME
        )
        bus.add_signal_receiver(
            self.__lost_server, 'LostServer',
            bus_name=SERVER_BUS_NAME
        )
        self.__get_servers()

    def __getitem__(self, udn):
        key = udn.lower()
        with self.__lock:
            return self.__servers[key]

    def __iter__(self):
        with self.__lock:
            return iter(list(self.__servers))

    def __len__(self):
        with self.__lock:
            return len(self.__servers)

    def __add_server(self, obj):
        udn = obj['UDN']
        obj['URI'] = uritools.uricompose('dleyna', udn)
        key = udn.lower()
        if key not in self:
            self.__log_server_action('Found', obj)
        with self.__lock:
            self.__servers[key] = obj

    def __remove_server(self, obj):
        key = obj['UDN'].lower()
        with self.__lock:
            del self.__servers[key]
        self.__log_server_action('Lost', obj)

    def __found_server(self, path):
        def error_handler(e):
            logger.warn('Cannot access media server %s: %s', path, e)

        self.__bus.get_object(SERVER_BUS_NAME, path).GetAll(
            '',  # all interfaces
            dbus_interface=dbus.PROPERTIES_IFACE,
            reply_handler=self.__add_server,
            error_handler=error_handler
        )

    def __lost_server(self, path):
        with self.__lock:
            servers = list(self.__servers.values())
        for obj in servers:
            if obj['Path'] == path:
                return self.__remove_server(obj)
        logger.info('Lost digital media server %s', path)

    def __get_servers(self):
        def reply_handler(paths):
            for path in paths:
                self.__found_server(path)

        def error_handler(e):
            logger.error('Cannot retrieve digital media servers: %s', e)

        self.__bus.get_object(SERVER_BUS_NAME, SERVER_ROOT_PATH).GetServers(
            dbus_interface=SERVER_MANAGER_IFACE,
            reply_handler=reply_handler,
            error_handler=error_handler
        )

    @classmethod
    def __log_server_action(cls, action, obj):
        logger.info(
            '%s digital media server %s [%s]',
            action, obj['FriendlyName'], obj['UDN']
        )


class dLeynaClient(object):

    MEDIA_CONTAINER_IFACE = 'org.gnome.UPnP.MediaContainer2'

    MEDIA_DEVICE_IFACE = 'com.intel.dLeynaServer.MediaDevice'

    MEDIA_ITEM_IFACE = 'org.gnome.UPnP.MediaItem2'

    MEDIA_OBJECT_IFACE = 'org.gnome.MediaObject2'

    def __init__(self, address=None, mainloop=None):
        if address:
            self.__bus = dbus.bus.BusConnection(address, mainloop=mainloop)
        else:
            self.__bus = dbus.SessionBus(mainloop=mainloop)
        self.__servers = dLeynaServers(self.__bus)

    def browse(self, uri, offset=0, limit=0, filter=['*']):
        baseuri, objpath = self.__parseuri(uri)
        future = dLeynaFuture.fromdbus(
            self.__bus.get_object(SERVER_BUS_NAME, objpath).ListChildren,
            dbus.UInt32(offset), dbus.UInt32(limit),
            translator.urifilter(filter),
            dbus_interface=self.MEDIA_CONTAINER_IFACE
        )
        if baseuri and (filter == ['*'] or 'URI' in filter):
            return future.map(translator.urimapper(baseuri))
        else:
            return future

    def properties(self, uri, iface=None):
        baseuri, objpath = self.__parseuri(uri)
        future = dLeynaFuture.fromdbus(
            self.__bus.get_object(SERVER_BUS_NAME, objpath).GetAll,
            iface or '',
            dbus_interface=dbus.PROPERTIES_IFACE
        )
        if baseuri and (not iface or iface == self.MEDIA_OBJECT_IFACE):
            return future.apply(translator.urimapper(baseuri))
        else:
            return future

    def rescan(self):
        return dLeynaFuture.fromdbus(
            self.__bus.get_object(SERVER_BUS_NAME, SERVER_ROOT_PATH).Rescan,
            dbus_interface=SERVER_MANAGER_IFACE
        )

    def search(self, uri, query, offset=0, limit=0, filter=['*']):
        baseuri, objpath = self.__parseuri(uri)
        future = dLeynaFuture.fromdbus(
            self.__bus.get_object(SERVER_BUS_NAME, objpath).SearchObjects,
            query, dbus.UInt32(offset), dbus.UInt32(limit),
            translator.urifilter(filter),
            dbus_interface=self.MEDIA_CONTAINER_IFACE
        )
        if baseuri and (filter == ['*'] or 'URI' in filter):
            return future.map(translator.urimapper(baseuri))
        else:
            return future

    def server(self, uri):
        udn = uritools.urisplit(uri).gethost()
        return dLeynaFuture.fromvalue(self.__servers[udn])

    def servers(self):
        return dLeynaFuture.fromvalue(self.__servers.values())

    def __parseuri(self, uri):
        parts = uritools.urisplit(uri)
        if parts.authority:
            udn = parts.gethost()
            try:
                server = self.__servers[udn]
            except KeyError:
                raise LookupError('Unknown media server UDN %s' % udn)
            else:
                return server['URI'], server['Path'] + parts.path
        else:
            return None, uri


if __name__ == '__main__':
    import argparse
    import json
    import sys

    import dbus.mainloop.glib
    import gobject

    parser = argparse.ArgumentParser()
    parser.add_argument('uri', nargs='?')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-f', '--filter', default=['*'], nargs='*')
    parser.add_argument('-i', '--indent', type=int, default=2)
    parser.add_argument('-l', '--list', action='store_true')
    parser.add_argument('-q', '--query')

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.ERROR)

    client = dLeynaClient(mainloop=dbus.mainloop.glib.DBusGMainLoop())
    # FIXME: wait for servers
    for i in range(0, 10000):
        gobject.MainLoop().get_context().iteration(True)

    if not args.uri:
        future = client.servers()
    elif args.list:
        future = client.browse(args.uri, filter=args.filter)
    elif args.query:
        future = client.search(args.uri, args.query, filter=args.filter)
    else:
        future = client.properties(args.uri)

    while True:
        try:
            future.get(timeout=0)
        except pykka.Timeout:
            gobject.MainLoop().get_context().iteration(True)
        else:
            break

    json.dump(future.get(), sys.stdout, default=vars, indent=args.indent)
    sys.stdout.write('\n')
