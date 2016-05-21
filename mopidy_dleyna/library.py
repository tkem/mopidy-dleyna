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

LOOKUP_FILTER = SEARCH_FILTER = [
    'Album',
    'AlbumArtURL',
    'Artist',
    'Artists',
    'Bitrate',
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


def iterate(func, translate, limit):
    def generate(future):
        offset = limit
        while future:
            objs, more = future.get()
            if more:
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
        ext_config = config[Extension.ext_name]
        self.__upnp_browse_limit = ext_config['upnp_browse_limit']
        self.__upnp_lookup_limit = ext_config['upnp_lookup_limit']
        self.__upnp_search_limit = ext_config['upnp_search_limit']

    def browse(self, uri):
        if uri == self.root_directory.uri:
            refs = sorted(self.__servers, key=operator.attrgetter('name'))
        else:
            refs = self.__browse(uri)
        return list(refs)

    def get_images(self, uris):
        # TODO: suggest as API improvement
        uris = frozenset(uris)
        # group uris by authority (media server)
        queries = collections.defaultdict(list)
        for uri in uris.difference([self.root_directory.uri]):
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
        if self.root_directory.uri in uris:
            result[self.root_directory.uri] = tuple()
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
            albums=result[models.Album].values(),
            artists=result[models.Artist].values(),
            tracks=result[models.Track].values()
        )

    def __browse(self, uri, filter=BROWSE_FILTER):
        client = self.backend.client
        obj = client.properties(uri, iface=client.MEDIA_OBJECT_IFACE).get()
        order = BROWSE_ORDER[translator.ref(obj).type]

        def browse(offset, limit):
            return client.browse(uri, offset, limit, filter, order).apply(
                lambda objs: (objs, limit and len(objs) == limit)
            )
        return iterate(browse, translator.ref, self.__upnp_browse_limit)

    def __images(self, baseuri, paths, filter=IMAGES_FILTER):
        client = self.backend.client
        server = client.server(baseuri).get()
        # fall back on properties if path search is not available/enabled
        if self.__upnp_lookup_limit == 1 or 'Path' not in server['SearchCaps']:
            futures = [client.properties(baseuri + path) for path in paths]
            return (translator.images(f.get()) for f in futures)
        # use path search for retrieving multiple results at once
        root = server['Path']

        def images(offset, limit):
            slice = paths[offset:offset + limit if limit else None]
            query = ' or '.join('Path = "%s%s"' % (root, p) for p in slice)
            return client.search(baseuri, query, 0, 0, filter).apply(
                lambda objs: (objs, limit and offset + limit < len(paths))
            )
        return iterate(images, translator.images, self.__upnp_lookup_limit)

    def __lookup(self, uri, filter=LOOKUP_FILTER):
        client = self.backend.client
        obj = client.properties(uri).get()
        if translator.ref(obj).type == models.Ref.TRACK:
            objs = [obj]
        else:
            objs = client.search(uri, LOOKUP_QUERY, filter=filter).get()
        return map(translator.track, objs)

    def __search(self, uri, query, exact, filter=SEARCH_FILTER):
        client = self.backend.client
        server = client.server(uri).get()
        q = translator.query(query or {}, exact, server['SearchCaps'])

        def search(offset, limit):
            return client.search(uri, q, offset, limit, filter).apply(
                lambda objs: (objs, limit and len(objs) == limit)
            )
        return iterate(search, translator.model, self.__upnp_search_limit)

    @property
    def __servers(self):
        for server in self.backend.client.servers().get():
            name = server.get('FriendlyName', server['DisplayName'])
            yield models.Ref.directory(name=name, uri=server['URI'])
