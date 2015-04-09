from __future__ import absolute_import, unicode_literals

import collections
import logging
import os

import dbus
import uritools

from mopidy import backend
from mopidy.models import Album, Artist, Ref, SearchResult, Track

from . import Extension
from .dleyna import ALBUM_TYPE_EX, ARTIST_TYPE_EX
from .dleyna import MANAGER_IFACE, SERVER_BUS_NAME, SERVER_ROOT_PATH
from .gupnp import MEDIA_CONTAINER_IFACE

logger = logging.getLogger(__name__)

# workaround for minidlna crashing on empty(?) search filters
# see https://github.com/01org/dleyna-server/issues/148
_BROWSE_FILTER = _SEARCH_FILTER = ['*']

_QUERY_MAPPING = [{
    'any': """
    DisplayName contains {0}
    or Album contains {0}
    or Artist contains {0}
    or Genre contains {0}
    """,
    # 'uri',
    'track_name': 'Type = "music" and DisplayName contains {0}',
    'album': 'Album contains {0}',
    'artist': 'Artist contains {0}',
    # 'composer',
    # 'performer',
    # 'albumartist',
    'genre': 'Genre contains {0}',
    'track_no': 'TrackNumber = {0}',
    'date': 'Date contains {0}',
    # 'comment'
}, {
    'any': 'DisplayName = {0} or Album = {0} or Artist = {0} or Genre = {0}',
    # 'uri',
    'track_name': 'Type = "music" and DisplayName = {0}',
    'album': 'Album = {0}',
    'artist': 'Artist = {0}',
    # 'composer',
    # 'performer',
    # 'albumartist',
    'genre': 'Genre = {0}',
    'track_no': 'TrackNumber = {0}',
    'date': 'Date = {0}',
    # 'comment'
}]

_SCHEME = Extension.ext_name


def _quote(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _name_to_uri(path, type_ex, name):
    root = os.path.dirname(path)  # TODO: obj['Parent']?
    query = 'TypeEx = %s and DisplayName = %s' % (type_ex, _quote(name))
    return uritools.uricompose(_SCHEME, path=root, query=query)


def _name_to_album(path, name):
    return Album(name=name, uri=_name_to_uri(path, ALBUM_TYPE_EX, name))


def _name_to_artist(path, name):
    return Artist(name=name, uri=_name_to_uri(path, ARTIST_TYPE_EX, name))


def _properties_to_ref(obj):
    name = obj['DisplayName']
    uri = uritools.uricompose(_SCHEME, path=obj['Path'])
    type_ex = obj.get('TypeEx', obj['Type'])
    if type_ex == ALBUM_TYPE_EX:
        return Ref.album(name=name, uri=uri)
    elif type_ex == ARTIST_TYPE_EX:
        return Ref.artist(name=name, uri=uri)
    elif type_ex == 'music' or type_ex == 'audio':
        return Ref.track(name=name, uri=uri)
    elif obj['Type'] == 'container':
        return Ref.directory(name=name, uri=uri)
    else:
        return None


def _properties_to_model(obj):
    type_ex = obj.get('TypeEx', obj['Type'])
    if type_ex == ALBUM_TYPE_EX:
        return _properties_to_album(obj)
    elif type_ex == ARTIST_TYPE_EX:
        return _properties_to_artist(obj)
    elif type_ex == 'music' or type_ex == 'audio':
        return _properties_to_track(obj)
    else:
        return None


def _properties_to_album(obj):
    path = obj['Path']
    if 'Creator' in obj:
        artists = [_name_to_artist(path, obj['Creator'])]
    else:
        artists = None
    return Album(
        uri=uritools.uricompose(_SCHEME, path=path),
        name=obj['DisplayName'],
        artists=artists,
        num_tracks=obj.get('ItemCount', obj.get('ChildCount')),
    )


def _properties_to_artist(obj):
    return Artist(
        uri=uritools.uricompose(_SCHEME, path=obj['Path']),
        name=obj['DisplayName']
    )


def _properties_to_track(obj):
    path = obj['Path']
    if 'Album' in obj:
        album = _name_to_album(path, obj['Album'])
    else:
        album = None
    if 'Artists' in obj:
        artists = [_name_to_artist(path, name) for name in obj['Artists']]
    elif 'Artist' in obj:
        artists = [_name_to_artist(path, obj['Artists'])]
    else:
        artists = None
    if 'Duration' in obj:
        length = obj['Duration'] * 1000
    else:
        length = None
    return Track(
        uri=uritools.uricompose(_SCHEME, path=path),
        name=obj['DisplayName'],
        artists=artists,
        album=album,
        date=obj.get('Date'),
        genre=obj.get('Genre'),
        length=length,
        track_no=obj.get('TrackNumber')
    )


class dLeynaLibraryProvider(backend.LibraryProvider):

    root_directory = Ref.directory(
        uri=uritools.uricompose(_SCHEME),
        name='Digital Media Servers'
    )

    def __init__(self, config, backend):
        super(dLeynaLibraryProvider, self).__init__(backend)
        self.__bus = dbus.SessionBus()

    def browse(self, uri):
        path = uritools.urisplit(uri).getpath()
        refs = []
        if path:
            container = self.__get_object(path, MEDIA_CONTAINER_IFACE)
            for obj in container.ListChildren(0, 0, _BROWSE_FILTER):
                ref = _properties_to_ref(obj)
                if ref:
                    refs.append(ref)
                else:
                    logger.debug('Skipping dLeyna browse result %r', obj)
        else:
            for obj in map(self.__get_properties, self.__get_server_paths()):
                name = obj.get('FriendlyName', obj['DisplayName'])
                uri = uritools.uricompose(_SCHEME, path=obj['Path'])
                refs.append(Ref.directory(name=name, uri=uri))
        return refs

    def get_images(self, uris):
        return {}  # TODO

    def lookup(self, uri):
        # TODO: check for query component
        path = uritools.urisplit(uri).getpath()
        obj = self.__get_properties(path)
        type = obj['Type']

        tracks = []
        if type == 'container':
            container = self.__get_object(path, MEDIA_CONTAINER_IFACE)
            for obj in container.ListItems(0, 0, _BROWSE_FILTER):
                track = _properties_to_track(obj)
                if track:
                    tracks.append(track)
                else:
                    logger.debug('Skipping dLeyna lookup result %r', obj)
        elif type == 'music' or 'type' == 'audio':
            tracks.append(_properties_to_track(obj))
        else:
            logger.warn('Invalid dLeyna type for %s: %s', uri, type)
        return tracks

    def refresh(self, uri=None):
        self.__get_object(SERVER_ROOT_PATH, MANAGER_IFACE).Rescan()

    def search(self, query=None, uris=None, exact=False):
        paths = set()
        for uri in uris or [self.root_directory.uri]:
            if uri == self.root_directory.uri:
                paths.update(self.__get_server_paths())
            else:
                paths.add(uritools.urisplit(uri).getpath())
        logger.debug('dLeyna search paths: %s', paths)

        if query:
            terms = []
            mapping = _QUERY_MAPPING[exact]
            for key, values in query.items():
                if key in mapping:
                    terms.extend(map(mapping[key].format, map(_quote, values)))
                else:
                    logger.warn('No dLeyna mapping for %s', key)
            query = '(%s)' % ') and ('.join(terms)
        else:
            query = '*'
        logger.debug('dLeyna search query: %s', query)

        # TODO: async method calls
        results = collections.defaultdict(list)
        for path in paths:
            container = self.__get_object(path, MEDIA_CONTAINER_IFACE)
            for obj in container.SearchObjects(query, 0, 0, _SEARCH_FILTER):
                model = _properties_to_model(obj)
                if model:
                    results[type(model)].append(model)
                else:
                    logger.debug('Skipping dLeyna search result %r', obj)
        return SearchResult(
            uri=uritools.uricompose(_SCHEME, query=query),
            albums=results[Album],
            artists=results[Artist],
            tracks=results[Track]
        )

    def __get_object(self, path, iface=None):
        obj = self.__bus.get_object(SERVER_BUS_NAME, path)
        if iface:
            return dbus.Interface(obj, iface)
        else:
            return obj

    def __get_properties(self, path):
        return self.__get_object(path, dbus.PROPERTIES_IFACE).GetAll('')

    def __get_server_paths(self):
        return self.__get_object(SERVER_ROOT_PATH, MANAGER_IFACE).GetServers()
