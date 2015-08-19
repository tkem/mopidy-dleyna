from __future__ import absolute_import, unicode_literals

import collections
import logging

from mopidy import backend
from mopidy.models import Album, Artist, Image, Ref, SearchResult, Track

from uritools import uricompose, urisplit

from . import Extension, translator

logger = logging.getLogger(__name__)


BROWSE_FILTER = [
    'DisplayName',
    'Path',
    'RefPath',
    'Type',
    'TypeEx'
]

IMAGES_FILTER = [
    'AlbumArtURL',
    'Path'
]

SEARCH_FILTER = [
    'Album',
    'AlbumArtURL',
    'Artist',
    'Artists',
    'Creator',
    'Date',
    'DisplayName',
    'Duration',
    'Genre',
    'Parent',
    'Path',
    'RefPath',
    'TrackNumber',
    'Type',
    'TypeEx',
]

LOOKUP_QUERY = 'Type = "music" or Type = "audio"'

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


def _quote(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


class dLeynaLibraryProvider(backend.LibraryProvider):

    root_directory = Ref.directory(
        uri=uricompose(Extension.ext_name),
        name='Digital Media Servers'
    )

    def browse(self, uri):
        refs = []
        dleyna = self.backend.dleyna
        if uri == self.root_directory.uri:
            for server in dleyna.servers().get():
                name = server['FriendlyName']
                uri = uricompose(Extension.ext_name, host=server['UDN'])
                refs.append(Ref.directory(name=name, uri=uri))
        else:
            parts = urisplit(uri)
            server = dleyna.server(parts.gethost()).get()
            baseuri = uricompose('dleyna', server['UDN'])
            path = server['Path'] + parts.getpath()
            future = dleyna.children(path, filter=BROWSE_FILTER)
            for obj in future.get():
                try:
                    ref = translator.ref(baseuri, obj)
                except ValueError as e:
                    logger.warn('Skipping dLeyna browse result: %s', e)
                else:
                    refs.append(ref)
        return refs

    def get_images(self, uris):
        dleyna = self.backend.dleyna
        servers = {obj['UDN']: obj for obj in dleyna.servers().get()}
        pathmap = collections.defaultdict(list)  # udn -> paths
        urimap = {}  # path -> uri
        for uri in uris:
            parts = urisplit(uri)
            udn = parts.gethost()
            path = servers[udn]['Path'] + parts.getpath()
            urimap[path] = uri
            pathmap[udn].append(path)
        futures = []
        for udn, paths in pathmap.items():
            futures.extend(self.__lookup(servers[udn], paths, IMAGES_FILTER))
        results = {}
        for obj in (obj for future in futures for obj in future.get()):
            try:
                image = Image(uri=obj['AlbumArtURL'])
            except KeyError:
                logger.debug('Skipping result without image: %s', obj['Path'])
                continue
            try:
                results[urimap[obj['Path']]] = [image]
            except KeyError:
                logger.warn('Unexpected dLeyna result path: %s', obj['Path'])
        return results

    def lookup(self, uri):
        dleyna = self.backend.dleyna
        uriparts = urisplit(uri)
        server = dleyna.server(uriparts.gethost()).get()
        baseuri = uricompose(Extension.ext_name, server['UDN'])
        path = server['Path'] + uriparts.getpath()
        properties = dleyna.properties(path).get()

        if properties['Type'] == 'container':
            future = dleyna.search(path, LOOKUP_QUERY, filter=SEARCH_FILTER)
            return [translator.track(baseuri, obj) for obj in future.get()]
        elif properties['Type'] in ('music', 'audio'):
            return [translator.track(baseuri, properties)]
        else:
            raise ValueError('Invalid type for %s: %s' % (uri, obj['Type']))

    def refresh(self, uri=None):
        logger.info('Refreshing dLeyna library')
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
                for server in self.backend.dleyna.servers().get():
                    uri = uricompose(Extension.ext_name, host=server['UDN'])
                    futures.append(self.__search(query, uri))
            else:
                futures.append(self.__search(query, uri))

        results = collections.defaultdict(list)
        for baseuri, objs in (f.get() for f in futures):
            for obj in objs:
                try:
                    model = translator.model(baseuri, obj)
                except ValueError:
                    logger.warn('Skipping dLeyna search result %r', obj)
                else:
                    results[type(model)].append(model)
        return SearchResult(
            uri=uricompose(Extension.ext_name, query=query),
            albums=results[Album],
            artists=results[Artist],
            tracks=results[Track]
        )

    # TODO: refactor (move to client?), configurable chunk size
    def __lookup(self, server, paths, filter=['*'], limit=10):
        dleyna = self.backend.dleyna
        futures = []
        root = server['Path']
        if 'Path' in server.get('SearchCaps', []):
            for n in range(0, len(paths), limit):
                chunk = paths[n:n+limit]
                query = ' or '.join('Path = "%s"' % path for path in chunk)
                futures.append(dleyna.search(root, query, 0, 0, filter))
        else:
            for path in paths:
                futures.append(dleyna.properties(path).apply(lambda x: [x]))
        return futures

    def __search(self, query, uri):
        dleyna = self.backend.dleyna
        uriparts = urisplit(uri)
        server = dleyna.server(uriparts.gethost()).get()
        baseuri = uricompose(Extension.ext_name, server['UDN'])
        path = server['Path'] + uriparts.getpath()
        future = dleyna.search(path, query, filter=SEARCH_FILTER)
        return future.apply(lambda result: (baseuri, result))
