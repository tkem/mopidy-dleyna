from __future__ import absolute_import, unicode_literals

import collections
import itertools
import logging
import operator

from mopidy import backend, models

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

LOOKUP_QUERY = 'Type = "music" or Type = "audio"'  # TODO: check SearchCaps?


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]


class dLeynaLibraryProvider(backend.LibraryProvider):

    root_directory = models.Ref.directory(
        uri=uricompose(Extension.ext_name),
        name='Digital Media Servers'
    )

    def __init__(self, config, backend):
        super(dLeynaLibraryProvider, self).__init__(backend)
        self.__config = config[Extension.ext_name]

    def browse(self, uri):
        if uri == self.root_directory.uri:
            return self.__browse_root()

        uriparts = urisplit(uri)
        dleyna = self.backend.dleyna
        server = dleyna.server(uriparts.gethost()).get()
        path = server['Path'] + uriparts.getpath()
        baseuri = uricompose('dleyna', server['UDN'])

        refs = []
        offset = limit = self.__config['upnp_browse_limit']
        future = dleyna.browse(path, 0, limit, BROWSE_FILTER)
        while future:
            objs = future.get()
            if limit and len(objs) == limit:
                future = dleyna.browse(path, offset, limit, BROWSE_FILTER)
            else:
                future = None
            for obj in objs:
                try:
                    ref = translator.ref(baseuri, obj)
                except ValueError as e:
                    logger.debug('Skipping %s: %s', obj['Path'], e)
                else:
                    refs.append(ref)
            offset += limit
        return refs

    def get_images(self, uris):
        dleyna = self.backend.dleyna
        servers = {obj['UDN']: obj for obj in dleyna.servers().get()}
        searchpaths = collections.defaultdict(list)  # for Path queries
        futures = []
        urimap = {}

        for uri in uris:
            parts = urisplit(uri)
            try:
                server = servers[parts.gethost()]
            except KeyError:
                raise LookupError('Cannot resolve URI %s' % uri)
            root = server['Path']
            path = root + parts.getpath()
            if 'Path' in server['SearchCaps']:
                searchpaths[root].append(path)
            else:
                futures.append(dleyna.properties(path).apply(lambda x: [x]))
            urimap[path] = uri

        for root, paths in searchpaths.items():
            # TODO: how to determine max. query size for server? config?
            for chunk in _chunks(paths, 50):
                query = ' or '.join('Path = "%s"' % path for path in chunk)
                futures.append(dleyna.search(root, query, 0, 0, IMAGES_FILTER))

        results = {}
        for obj in itertools.chain.from_iterable(f.get() for f in futures):
            try:
                uri = urimap[obj['Path']]
            except KeyError:
                logger.error('Unexpected path in image result: %r', obj)
            else:
                results[uri] = translator.images(obj)
        return results

    def lookup(self, uri):
        uriparts = urisplit(uri)
        dleyna = self.backend.dleyna
        server = dleyna.server(uriparts.gethost()).get()
        path = server['Path'] + uriparts.getpath()
        baseuri = uricompose(Extension.ext_name, server['UDN'])
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
        futures = []
        for uri in self.__urifilter(uris):
            try:
                future = self.__search(query or {}, uri, exact)
            except ValueError as e:
                logger.warn('Not searching %s: %s', uri, e)
            else:
                futures.append(future)
        results = collections.defaultdict(collections.OrderedDict)
        for model in itertools.chain.from_iterable(f.get() for f in futures):
            results[type(model)][model.uri] = model  # merge results w/same uri
        return models.SearchResult(
            uri=uricompose(Extension.ext_name, query=query),
            albums=results[models.Album].values(),
            artists=results[models.Artist].values(),
            tracks=results[models.Track].values()
        )

    def __browse_root(self):
        refs = []
        for server in self.backend.dleyna.servers().get():
            name = server['FriendlyName']  # mandatory for server
            uri = uricompose(Extension.ext_name, host=server['UDN'])
            refs.append(models.Ref.directory(name=name, uri=uri))
        return list(sorted(refs, key=operator.attrgetter('name')))

    def __search(self, query, uri, exact=False):
        uriparts = urisplit(uri)
        dleyna = self.backend.dleyna
        server = dleyna.server(uriparts.gethost()).get()
        path = server['Path'] + uriparts.getpath()
        query = translator.query(query, exact, server['SearchCaps'])
        limit = self.__config['upnp_search_limit']
        future = dleyna.search(path, query, 0, limit, SEARCH_FILTER)

        def models(objs):
            baseuri = uricompose(Extension.ext_name, server['UDN'])
            for obj in objs:
                try:
                    yield translator.model(baseuri, obj)
                except ValueError as e:
                    logger.debug('Skipping %s: %s', obj['Path'], e)
        return future.apply(models)

    def __urifilter(self, uris=None):
        uriset = set(uris or [self.root_directory.uri])
        if self.root_directory.uri in uriset:
            for server in self.backend.dleyna.servers().get():
                uriset.add(uricompose(Extension.ext_name, host=server['UDN']))
            uriset.remove(self.root_directory.uri)
        return iter(uriset)
