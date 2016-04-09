from __future__ import absolute_import, unicode_literals

import collections
import itertools
import logging
import operator

from mopidy import backend, models

import uritools

from . import Extension, translator

logger = logging.getLogger(__name__)

BROWSE_FILTER = [
    'DisplayName',
    'Type',
    'TypeEx',
    'URI'
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
    'TrackNumber',
    'Type',
    'TypeEx',
    'URI'
]

BROWSE_ORDER = {
    models.Ref.ALBUM: ['+TrackNumber', '+DisplayName'],
    models.Ref.ARTIST: ['+TypeEx', '+DisplayName'],
    models.Ref.DIRECTORY: ['+TypeEx', '+DisplayName'],
}

LOOKUP_QUERY = 'Type = "music" or Type = "audio"'  # TODO: check SearchCaps


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]


def iterate(func, translate, limit):
    def generate(future):
        offset = limit
        while future:
            objs = future.get()
            if limit and len(objs) == limit:
                future = func(offset, limit)
            else:
                future = None
            for obj in objs:
                try:
                    result = translate(obj)
                except ValueError as e:
                    logger.debug('Skipping %s: %s', obj.get('URI'), e)
                else:
                    yield result
            offset += limit
    return generate(func(0, limit))


class dLeynaLibraryProvider(backend.LibraryProvider):

    root_directory = models.Ref.directory(
        uri=uritools.uricompose(Extension.ext_name),
        name='Digital Media Servers'
    )

    def __init__(self, backend, config):
        super(dLeynaLibraryProvider, self).__init__(backend)
        self.__upnp_search_limit = config['upnp_search_limit']
        self.__upnp_browse_limit = config['upnp_browse_limit']

    def browse(self, uri):
        if uri == self.root_directory.uri:
            refs = sorted(self.__servers, key=operator.attrgetter('name'))
        else:
            refs = self.__browse(uri)
        return list(refs)

    def get_images(self, uris):
        client = self.backend.client
        servers = {obj['UDN']: obj for obj in client.servers().get()}
        searchpaths = collections.defaultdict(list)  # for Path queries
        futures = []
        urimap = {}
        # TODO: refactor for URIs
        for uri in uris:
            parts = uritools.urisplit(uri)
            try:
                server = servers[parts.gethost()]
            except KeyError:
                raise LookupError('Cannot resolve URI %s' % uri)
            root = server['Path']
            path = root + parts.getpath()
            if 'Path' in server['SearchCaps']:
                searchpaths[root].append(path)
            else:
                futures.append(client.properties(path).apply(lambda x: [x]))
            urimap[path] = uri

        for root, paths in searchpaths.items():
            # TODO: how to determine max. query size for server? config?
            for chunk in _chunks(paths, 50):
                query = ' or '.join('Path = "%s"' % path for path in chunk)
                futures.append(client.search(root, query, 0, 0, IMAGES_FILTER))

        results = {}
        for obj in itertools.chain.from_iterable(f.get() for f in futures):
            try:
                uri = urimap[obj['Path']]
            except KeyError:
                logger.error('Unexpected path in image result: %r', obj)
            else:
                results[uri] = list(translator.images(obj))
        return results

    def lookup(self, uri):
        if uri == self.root_directory.uri:
            tracks = []
        else:
            tracks = self.__lookup(uri)
        return list(tracks)

    def refresh(self, uri=None):
        logger.info('Refreshing dLeyna library')
        self.backend.client.rescan().get()

    def search(self, query=None, uris=None, exact=False):
        # sanitize uris - remove duplicates, replace root with server uris
        uris = set(uris or [self.root_directory.uri])
        if self.root_directory.uri in uris:
            uris.update(ref.uri for ref in self.__servers)
            uris.remove(self.root_directory.uri)
        # start searching - blocks only when iterating over results
        results = []
        for uri in uris:
            try:
                iterable = self.__search(uri, query, exact)
            except NotImplementedError as e:
                logger.warn('Not searching %s: %s', uri, e)
            else:
                results.append(iterable)
        if not results:
            return None
        # retrieve and merge search results - TODO: handle exceptions?
        result = collections.defaultdict(collections.OrderedDict)
        for model in itertools.chain.from_iterable(results):
            result[type(model)][model.uri] = model
        return models.SearchResult(
            uri=uritools.uricompose(Extension.ext_name, query=query),
            albums=result[models.Album].values(),
            artists=result[models.Artist].values(),
            tracks=result[models.Track].values()
        )

    def __browse(self, uri):
        client = self.backend.client
        obj = client.properties(uri, iface=client.MEDIA_OBJECT_IFACE).get()
        order = BROWSE_ORDER[translator.ref(obj).type]

        def browse(offset, limit):
            return client.browse(uri, offset, limit, BROWSE_FILTER, order)
        return iterate(browse, translator.ref, self.__upnp_browse_limit)

    def __lookup(self, uri):
        client = self.backend.client
        obj = client.properties(uri).get()
        if translator.ref(obj).type == models.Ref.TRACK:
            objs = [obj]
        else:
            objs = client.search(uri, LOOKUP_QUERY, filter=SEARCH_FILTER).get()
        return map(translator.track, objs)

    def __search(self, uri, query, exact):
        client = self.backend.client
        # TODO: better handling of searchcaps?
        searchcaps = client.server(uri).get().get('SearchCaps', [])
        q = translator.query(query or {}, exact, searchcaps)

        def search(offset, limit):
            return client.search(uri, q, offset, limit, SEARCH_FILTER)
        return iterate(search, translator.model, self.__upnp_search_limit)

    @property
    def __servers(self):
        for server in self.backend.client.servers().get():
            name = server.get('FriendlyName', server['DisplayName'])
            yield models.Ref.directory(name=name, uri=server['URI'])
