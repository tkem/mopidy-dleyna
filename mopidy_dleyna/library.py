from __future__ import absolute_import, unicode_literals

import collections
import itertools
import logging
import operator

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


class dLeynaLibraryProvider(backend.LibraryProvider):

    root_directory = Ref.directory(
        uri=uricompose(Extension.ext_name),
        name='Digital Media Servers'
    )

    def browse(self, uri):
        if uri == self.root_directory.uri:
            return self.__browse_root()
        uriparts = urisplit(uri)
        dleyna = self.backend.dleyna
        server = dleyna.server(uriparts.gethost()).get()
        path = server['Path'] + uriparts.getpath()
        future = dleyna.children(path, filter=BROWSE_FILTER)

        refs = []
        baseuri = uricompose('dleyna', server['UDN'])
        for obj in future.get():
            try:
                ref = translator.ref(baseuri, obj)
            except ValueError as e:
                logger.debug('Skipping %s: %s', obj['Path'], e)
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
            logger.error('Invalid object type for %s: %s', uri, obj['Type'])

    def refresh(self, uri=None):
        logger.info('Refreshing dLeyna library')
        self.backend.dleyna.rescan()

    def search(self, query=None, uris=None, exact=False):
        limit = None  # TODO: config?
        futures = []
        for uri in self.__uriset(uris):
            try:
                future = self.__search(query or {}, uri, limit, exact=exact)
            except ValueError as e:
                logger.warn('Not searching %s: %s', uri, e)
            else:
                futures.append(future)
        results = collections.defaultdict(collections.OrderedDict)
        for model in itertools.chain.from_iterable(f.get() for f in futures):
            results[type(model)][model.uri] = model  # merge results w/same uri
        return SearchResult(
            uri=uricompose(Extension.ext_name, query=query),
            albums=results[Album].values(),
            artists=results[Artist].values(),
            tracks=results[Track].values()
        )

    def __browse_root(self):
        refs = []
        for server in self.backend.dleyna.servers().get():
            uri = uricompose(Extension.ext_name, host=server['UDN'])
            refs.append(Ref.directory(name=server['FriendlyName'], uri=uri))
        return list(sorted(refs, key=operator.attrgetter('name')))

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

    def __search(self, query, uri, limit=None, offset=0, exact=False):
        uriparts = urisplit(uri)
        dleyna = self.backend.dleyna
        server = dleyna.server(uriparts.gethost()).get()
        query = translator.query(query, exact, server['SearchCaps'])
        path = server['Path'] + uriparts.getpath()
        logger.debug('Search %s: %s', path, query)
        future = dleyna.search(path, query, offset, limit or 0, SEARCH_FILTER)

        def models(objs):
            baseuri = uricompose(Extension.ext_name, server['UDN'])
            for obj in objs:
                try:
                    yield translator.model(baseuri, obj)
                except ValueError as e:
                    logger.debug('Skipping %s: %s', obj['Path'], e)
        return future.apply(models)

    def __uriset(self, uris=None):
        uris = set(uris or [self.root_directory.uri])  # filter duplicates
        if self.root_directory.uri in uris:
            for server in self.backend.dleyna.servers().get():
                uris.add(uricompose(Extension.ext_name, host=server['UDN']))
            uris.remove(self.root_directory.uri)
        return uris
