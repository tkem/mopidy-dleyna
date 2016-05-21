from __future__ import absolute_import, unicode_literals

import collections
import logging
import threading
import time

import dbus

import uritools

from . import Extension, util

SERVER_BUS_NAME = 'com.intel.dleyna-server'

SERVER_ROOT_PATH = '/com/intel/dLeynaServer'

SERVER_MANAGER_IFACE = 'com.intel.dLeynaServer.Manager'

logger = logging.getLogger(__name__)


def urifilter(fields):
    if 'URI' in fields:
        objfilter = fields[:]
        objfilter.remove('URI')
        objfilter.append('Path')
        objfilter.append('RefPath')
        return objfilter
    else:
        return fields


def urimapper(baseuri, prefix='/com/intel/dLeynaServer/server/'):
    def mapper(obj, index=len(prefix)):
        objpath = obj.get('RefPath', obj['Path'])
        assert objpath.startswith(prefix)
        _, sep, relpath = objpath[index:].partition('/')
        obj['URI'] = baseuri + sep + relpath
        return obj
    return mapper


class Servers(collections.Mapping):

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
        obj['URI'] = uritools.uricompose(Extension.ext_name, udn)
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

    MEDIA_OBJECT_IFACE = 'org.gnome.UPnP.MediaObject2'

    def __init__(self, address=None, mainloop=None):
        if address:
            self.__bus = dbus.bus.BusConnection(address, mainloop=mainloop)
        else:
            self.__bus = dbus.SessionBus(mainloop=mainloop)
        self.__servers = Servers(self.__bus)

    def browse(self, uri, offset=0, limit=0, filter=['*'], order=[]):
        baseuri, objpath = self.__parseuri(uri)
        future = util.Future.fromdbus(
            self.__bus.get_object(SERVER_BUS_NAME, objpath).ListChildrenEx,
            dbus.UInt32(offset), dbus.UInt32(limit), urifilter(filter),
            ','.join(self.__sortorder(uri, order)),
            dbus_interface=self.MEDIA_CONTAINER_IFACE
        )
        if baseuri and (filter == ['*'] or 'URI' in filter):
            return future.map(urimapper(baseuri))
        else:
            return future

    def properties(self, uri, iface=None):
        baseuri, objpath = self.__parseuri(uri)
        future = util.Future.fromdbus(
            self.__bus.get_object(SERVER_BUS_NAME, objpath).GetAll,
            iface or '',
            dbus_interface=dbus.PROPERTIES_IFACE
        )
        if baseuri and (not iface or iface == self.MEDIA_OBJECT_IFACE):
            return future.apply(urimapper(baseuri))
        else:
            return future

    def rescan(self):
        return util.Future.fromdbus(
            self.__bus.get_object(SERVER_BUS_NAME, SERVER_ROOT_PATH).Rescan,
            dbus_interface=SERVER_MANAGER_IFACE
        )

    def search(self, uri, query, offset=0, limit=0, filter=['*'], order=[]):
        baseuri, objpath = self.__parseuri(uri)
        future = util.Future.fromdbus(
            self.__bus.get_object(SERVER_BUS_NAME, objpath).SearchObjectsEx,
            query, dbus.UInt32(offset), dbus.UInt32(limit), urifilter(filter),
            ','.join(self.__sortorder(uri, order)),
            dbus_interface=self.MEDIA_CONTAINER_IFACE
        )
        if baseuri and (filter == ['*'] or 'URI' in filter):
            return future.apply(lambda res: map(urimapper(baseuri), res[0]))
        else:
            return future.apply(lambda res: res[0])

    def server(self, uri):
        # return future for consistency/future extensions
        return util.Future.fromvalue(self.__server(uri))

    def servers(self):
        # return future for consistency/future extensions
        return util.Future.fromvalue(self.__servers.values())

    def __parseuri(self, uri):
        try:
            server = self.__server(uri)
        except ValueError:
            return None, uri
        else:
            return server['URI'], server['Path'] + uritools.urisplit(uri).path

    def __sortorder(self, uri, order):
        try:
            server = self.__server(uri)
        except ValueError:
            sortcaps = frozenset('*')
        else:
            sortcaps = frozenset(server.get('SortCaps', []))
        if '*' in sortcaps:
            return order
        else:
            return list(filter(lambda f: f[1:] in sortcaps, order))

    def __server(self, uri):
        udn = uritools.urisplit(uri).gethost()
        if not udn:
            raise ValueError('Invalid URI %s' % uri)
        try:
            server = self.__servers[udn]
        except KeyError:
            raise LookupError('Unknown media server UDN %s' % udn)
        else:
            return server


if __name__ == '__main__':  # pragma: no cover
    import argparse
    import json
    import sys

    import dbus.mainloop.glib
    import gobject

    parser = argparse.ArgumentParser()
    parser.add_argument('uri', metavar='PATH | URI', nargs='?')
    parser.add_argument('-b', '--browse', action='store_true')
    parser.add_argument('-f', '--filter', default=['*'], nargs='*')
    parser.add_argument('-i', '--iface')
    parser.add_argument('-m', '--offset', default=0, type=int)
    parser.add_argument('-n', '--limit', default=0, type=int)
    parser.add_argument('-o', '--order', default=[], nargs='*')
    parser.add_argument('-q', '--query')
    parser.add_argument('-t', '--timeout', default=1.0, type=float)
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARN)

    client = dLeynaClient(mainloop=dbus.mainloop.glib.DBusGMainLoop())

    start = time.time()
    while time.time() < start + args.timeout:
        if args.uri:
            try:
                client.server(args.uri).get()
            except LookupError:
                pass
            except ValueError:
                break  # D-BUS path given
            else:
                break
        gobject.MainLoop().get_context().iteration(False)

    kwargs = {
        'offset': args.offset,
        'limit': args.limit,
        'filter': args.filter,
        'order': args.order
    }

    if not args.uri:
        future = client.servers()
    elif args.browse:
        future = client.browse(args.uri, **kwargs)
    elif args.query:
        future = client.search(args.uri, args.query, **kwargs)
    else:
        future = client.properties(args.uri, iface=args.iface)

    while True:
        try:
            future.get(timeout=0)
        except util.Future.Timeout:
            gobject.MainLoop().get_context().iteration(True)
        else:
            break

    json.dump(future.get(), sys.stdout, default=vars, indent=2)
    sys.stdout.write('\n')
