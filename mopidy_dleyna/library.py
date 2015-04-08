from __future__ import unicode_literals

import logging

import dbus

from mopidy import backend
from mopidy.models import Album, Artist, Ref, Track

from .dleyna import MANAGER_IFACE, MEDIA_CONTAINER_IFACE
from .dleyna import SERVER_BUS_NAME, SERVER_ROOT_PATH

logger = logging.getLogger(__name__)

_BROWSE_FILTER = ['*']


def _item_to_track(props):
    return Track(
        name=props.get('DisplayName'),
        uri='dleyna:'+props.get('Path'),
        artists=[Artist(name=props.get('Artist'))],
        album=Album(name=props.get('Album')),
        date=props.get('Date'),
        genre=props.get('Genre'),
        length=int(props.get('Duration', 0)*1000),
        track_no=props.get('TrackNumber')
    )


class dLeynaLibraryProvider(backend.LibraryProvider):

    root_directory = Ref.directory(
        uri='dleyna:',
        name='DLNA Media Servers'
    )

    def __init__(self, config, backend):
        super(dLeynaLibraryProvider, self).__init__(backend)
        self.__bus = dbus.SessionBus()

    def browse(self, uri):
        _, _, path = uri.partition(':')

        refs = []
        if path:
            container = self.__get_object(path, MEDIA_CONTAINER_IFACE)
            for obj in container.ListChildren(0, 0, _BROWSE_FILTER):
                name = obj.get('DisplayName', obj['Path'])
                uri = 'dleyna:' + obj['Path']
                if obj['Type'] == 'container':
                    # TODO: album, playlist, ...
                    refs.append(Ref.directory(name=name, uri=uri))
                else:
                    refs.append(Ref.track(name=name, uri=uri))
        else:
            manager = self.__get_object(SERVER_ROOT_PATH, MANAGER_IFACE)
            for obj in map(self.__get_properties, manager.GetServers()):
                name = obj.get('FriendlyName', obj.get('DisplayName'))
                uri = 'dleyna:' + obj['Path']
                refs.append(Ref.directory(name=name, uri=uri))
        return refs

    def lookup(self, uri):
        _, _, path = uri.partition(':')
        props = self.__get_properties(path)
        if props.get('Type') == 'music':
            return [_item_to_track(props)]
        else:
            return []  # TODO: lookup containers, etc.

    def refresh(self, uri=None):
        self.__get_object(SERVER_ROOT_PATH, MANAGER_IFACE).Rescan()

    def __get_object(self, path, iface=None):
        obj = self.__bus.get_object(SERVER_BUS_NAME, path)
        if iface:
            return dbus.Interface(obj, iface)
        else:
            return obj

    def __get_properties(self, path):
        return self.__get_object(path, dbus.PROPERTIES_IFACE).GetAll('')
