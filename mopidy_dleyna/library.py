from __future__ import absolute_import, unicode_literals

import collections
import logging
import os

from mopidy import backend
from mopidy.models import Album, Artist, Ref, SearchResult, Track

import pykka

from uritools import uricompose, urisplit

from . import Extension

logger = logging.getLogger(__name__)


ALBUM_TYPE_EX = 'container.album.musicAlbum'

ARTIST_TYPE_EX = 'container.person.musicArtist'


# workaround for minidlna crashing on empty(?) search filters
# see https://github.com/01org/dleyna-server/issues/148
BROWSE_FILTER = SEARCH_FILTER = ['*']

QUERY_MAPPING = [{
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

SCHEME = Extension.ext_name


def _quote(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _name_to_uri(path, type_ex, name):
    root = os.path.dirname(path)  # TODO: obj['Parent']?
    query = 'TypeEx = %s and DisplayName = %s' % (type_ex, _quote(name))
    return uricompose(SCHEME, path=root, query=query)


def _name_to_album(path, name):
    return Album(name=name, uri=_name_to_uri(path, ALBUM_TYPE_EX, name))


def _name_to_artist(path, name):
    return Artist(name=name, uri=_name_to_uri(path, ARTIST_TYPE_EX, name))


def _properties_to_ref(server, obj):
    assert obj['Path'].startswith(server['Path'])
    path = obj['Path'][len(server['Path']):]
    uri = uricompose(SCHEME, host=server['UDN'], path=path)
    name = obj['DisplayName']
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


def _properties_to_model(server, obj):
    type_ex = obj.get('TypeEx', obj['Type'])
    if type_ex == ALBUM_TYPE_EX:
        return _properties_to_album(server, obj)
    elif type_ex == ARTIST_TYPE_EX:
        return _properties_to_artist(server, obj)
    elif type_ex == 'music' or type_ex == 'audio':
        return _properties_to_track(server, obj)
    else:
        return None


def _properties_to_album(server, obj):
    assert obj['Path'].startswith(server['Path'])
    path = obj['Path'][len(server['Path']):]
    if 'Creator' in obj:
        artists = [_name_to_artist(path, obj['Creator'])]
    else:
        artists = None
    return Album(
        uri=uricompose(SCHEME, host=server['UDN'], path=path),
        name=obj['DisplayName'],
        artists=artists,
        num_tracks=obj.get('ItemCount', obj.get('ChildCount')),
    )


def _properties_to_artist(server, obj):
    assert obj['Path'].startswith(server['Path'])
    path = obj['Path'][len(server['Path']):]
    return Artist(
        uri=uricompose(SCHEME, host=server['UDN'], path=path),
        name=obj['DisplayName']
    )


def _properties_to_track(server, obj):
    assert obj['Path'].startswith(server['Path'])
    path = obj['Path'][len(server['Path']):]
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
        uri=uricompose(SCHEME, host=server['UDN'], path=path),
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
        uri=uricompose(SCHEME),
        name='Digital Media Servers'
    )

    def browse(self, uri):
        refs = []
        dleyna = self.backend.dleyna
        if uri == self.root_directory.uri:
            for server in dleyna.servers():
                name = server.get('FriendlyName', server['DisplayName'])
                uri = uricompose(SCHEME, host=server['UDN'])
                refs.append(Ref.directory(name=name, uri=uri))
        else:
            parts = urisplit(uri)
            server = dleyna.get_server(parts.gethost())
            container = dleyna.get_container(server['Path'] + parts.getpath())
            for obj in container.ListChildren(0, 0, BROWSE_FILTER):
                ref = _properties_to_ref(server, obj)
                if ref:
                    refs.append(ref)
                else:
                    logger.debug('Skipping dLeyna browse result %r', obj)
        return refs

    def get_images(self, uris):
        return {}  # TODO

    def lookup(self, uri):
        parts = urisplit(uri)
        dleyna = self.backend.dleyna
        server = dleyna.get_server(parts.gethost())
        path = server['Path'] + parts.getpath()
        props = dleyna.get_properties(path)
        type = props['Type']

        tracks = []
        # TODO: test on iface?
        if type == 'container':
            # TODO: recursive/search?
            container = dleyna.get_container(path)
            for obj in container.ListItems(0, 0, BROWSE_FILTER):
                track = _properties_to_track(server, obj)
                if track:
                    tracks.append(track)
                else:
                    logger.debug('Skipping dLeyna lookup result %r', obj)
        elif type == 'music' or type == 'audio':
            tracks.append(_properties_to_track(server, props))
        else:
            logger.warn('Invalid dLeyna type for %s: %s', uri, type)
        return tracks

    def refresh(self, uri=None):
        self.backend.dleyna.rescan()

    def search(self, query=None, uris=None, exact=False):
        if query:
            terms = []
            mapping = QUERY_MAPPING[exact]
            for key, values in query.items():
                if key in mapping:
                    terms.extend(map(mapping[key].format, map(_quote, values)))
                else:
                    return None  # no mapping
            query = '(%s)' % ') and ('.join(terms)
        else:
            query = '*'
        logger.debug('dLeyna search query: %s', query)

        futures = []
        for uri in uris or [self.root_directory.uri]:
            if uri == self.root_directory.uri:
                for server in self.backend.dleyna.servers():
                    uri = uricompose(SCHEME, host=server['UDN'])
                    futures.append(self.__search(query, uri))
            else:
                futures.append(self.__search(query, uri))

        results = collections.defaultdict(list)
        for server, objs in pykka.get_all(futures):
            for obj in objs:
                model = _properties_to_model(server, obj)
                if model:
                    results[type(model)].append(model)
                else:
                    logger.debug('Skipping dLeyna search result %r', obj)
        return SearchResult(
            uri=uricompose(SCHEME, query=query),
            albums=results[Album],
            artists=results[Artist],
            tracks=results[Track]
        )

    def __search(self, query, uri):
        parts = urisplit(uri)
        dleyna = self.backend.dleyna
        server = dleyna.get_server(parts.gethost())
        future = pykka.ThreadingFuture()

        def reply_handler(objs):
            future.set((server, objs))

        def error_handler(e):
            future.set_exception(exc_info=(type(e), e, None))

        dleyna.get_container(server['Path'] + parts.getpath()).SearchObjects(
            query, 0, 0, SEARCH_FILTER,
            reply_handler=reply_handler,
            error_handler=error_handler
        )
        return future
