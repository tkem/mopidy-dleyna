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
    'URI'
]

SEARCH_FILTER = [
    'Album',
    'AlbumArtURL',
    'Artist',
    'Artists',
    'Bitrate',
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
        self.__upnp_browse_limit = config['upnp_browse_limit']
        self.__upnp_lookup_limit = config['upnp_lookup_limit']
        self.__upnp_search_limit = config['upnp_search_limit']

    def browse(self, uri):
        if uri == self.root_directory.uri:
            refs = sorted(self.__servers, key=operator.attrgetter('name'))
        else:
            refs = self.__browse(uri)
        return list(refs)

    def get_images(self, uris):
        # group uris by authority (media server)
        queries = collections.defaultdict(list)
        for uri in frozenset(uris).difference([self.root_directory.uri]):
            parts = uritools.urisplit(uri)
            baseuri = parts.scheme + '://' + parts.authority
            queries[baseuri].append(parts.path)
        # start searching - blocks only when iterating over results
        results = []
        for baseuri, paths in queries.items():
            try:
                iterable = self.__images(baseuri, paths)
            except NotImplementedError as e:
                logger.warn('Not retrieving images for %s: %s', baseuri, e)
            else:
                results.append(iterable)
        # merge results
        result = {}
        for uri, images in itertools.chain.from_iterable(results):
            result[uri] = tuple(images)
        return result

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

    def __images(self, baseuri, paths):
        client = self.backend.client
        server = client.server(baseuri).get()
        # iteratively retrieve props if path search is not available
        if 'Path' not in server['SearchCaps']:
            futures = [client.properties(baseuri + path) for path in paths]
            return (translator.images(f.get()) for f in futures)
        # TODO: client method?
        root = server['Path']

        def images(offset, limit):
            slice = paths[offset:offset + limit if limit else None]
            query = ' or '.join('Path = "%s%s"' % (root, p) for p in slice)
            return client.search(baseuri, query, 0, 0, IMAGES_FILTER)
        return iterate(images, translator.images, self.__upnp_lookup_limit)

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
        server = client.server(uri).get()
        q = translator.query(query or {}, exact, server['SearchCaps'])

        def search(offset, limit):
            return client.search(uri, q, offset, limit, SEARCH_FILTER)
        return iterate(search, translator.model, self.__upnp_search_limit)

    @property
    def __servers(self):
        for server in self.backend.client.servers().get():
            name = server.get('FriendlyName', server['DisplayName'])
            yield models.Ref.directory(name=name, uri=server['URI'])
