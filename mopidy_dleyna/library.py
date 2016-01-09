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


def _objmapper(func):
    def mapper(objs):
        for obj in objs:
            try:
                yield func(obj)
            except ValueError as e:
                logger.debug('Skipping %s: %s', obj['URI'], e)
    return mapper


class dLeynaLibraryProvider(backend.LibraryProvider):

    root_directory = models.Ref.directory(
        uri=uricompose(Extension.ext_name),
        name='Digital Media Servers'
    )

    def __init__(self, backend, config):
        super(dLeynaLibraryProvider, self).__init__(backend)
        self.__upnp_search_limit = config['upnp_search_limit']
        self.__upnp_browse_limit = config['upnp_browse_limit']

    def browse(self, uri):
        if uri == self.root_directory.uri:
            return self.__browse_root()
        else:
            return self.__browse_container(uri)

    def get_images(self, uris):
        dleyna = self.backend.dleyna
        servers = {obj['UDN']: obj for obj in dleyna.servers().get()}
        searchpaths = collections.defaultdict(list)  # for Path queries
        futures = []
        urimap = {}
        # TODO: refactor for URIs
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
        dleyna = self.backend.dleyna
        obj = dleyna.properties(uri).get()
        if obj['Type'] == 'container':
            future = dleyna.search(uri, LOOKUP_QUERY, filter=SEARCH_FILTER)
            return list(map(translator.track, future.get()))
        elif obj['Type'] in ('music', 'audio'):
            return [translator.track(obj)]
        else:
            logger.error('Invalid object type for %s: %s', uri, obj['Type'])
            return []

    def refresh(self, uri=None):
        logger.info('Refreshing dLeyna library')
        self.backend.dleyna.rescan().get()

    def search(self, query=None, uris=None, exact=False):
        dleyna = self.backend.dleyna
        # sanitize uris
        uris = set(uris or [self.root_directory.uri])
        if self.root_directory.uri in uris:
            uris.update(server['URI'] for server in dleyna.servers().get())
            uris.remove(self.root_directory.uri)
        # start searching
        futures = []
        for uri in uris:
            try:
                limit = self.__upnp_search_limit
                future = self.__search(uri, query or {}, exact, 0, limit)
            except ValueError as e:
                logger.warn('Not searching %s: %s', uri, e)
            else:
                futures.append(future)
        # retrieve and merge search results
        results = collections.defaultdict(collections.OrderedDict)
        for model in itertools.chain.from_iterable(f.get() for f in futures):
            results[type(model)][model.uri] = model  # merge results w/same uri
        return models.SearchResult(
            uri=uricompose(Extension.ext_name, query=query),
            albums=results[models.Album].values(),
            artists=results[models.Artist].values(),
            tracks=results[models.Track].values()
        )

    def __browse_root(self, key=operator.attrgetter('name')):
        refs = []
        for server in self.backend.dleyna.servers().get():
            name = server.get('FriendlyName', server['DisplayName'])
            refs.append(models.Ref.directory(name=name, uri=server['URI']))
        return list(sorted(refs, key=key))

    def __browse_container(self, uri):
        # determine sort order
        dleyna = self.backend.dleyna
        obj = dleyna.properties(uri, iface=dleyna.MEDIA_OBJECT_IFACE).get()
        order = self.__sortorder(uri, BROWSE_ORDER[translator.ref(obj).type])
        # start browsing
        refs = []
        offset = 0
        limit = self.__upnp_browse_limit
        future = self.__browse(uri, offset, limit, order)
        while future:
            result, more = future.get()
            if more:
                offset += limit
                future = self.__browse(uri, offset, limit, order)
            else:
                future = None
            refs.extend(result)
        return refs

    def __browse(self, uri, offset=0, limit=0, order=[],
                 mapper=_objmapper(translator.ref)):
        dleyna = self.backend.dleyna
        future = dleyna.browse(uri, offset, limit, BROWSE_FILTER, order)
        return future.apply(
            lambda objs: (mapper(objs), limit and len(objs) == limit)
        )

    def __search(self, uri, query, exact=False, offset=0, limit=0, order=[],
                 mapper=_objmapper(translator.model)):
        dleyna = self.backend.dleyna
        searchcaps = dleyna.server(uri).get().get('SearchCaps', [])
        logger.debug('SearchCaps for %s: %r', uri, searchcaps)
        query = translator.query(query, exact, searchcaps)
        future = dleyna.search(uri, query, offset, limit, SEARCH_FILTER, order)
        # TODO: return "more" flag as in browse
        return future.apply(mapper)

    def __sortorder(self, uri, order):
        dleyna = self.backend.dleyna
        sortcaps = frozenset(dleyna.server(uri).get().get('SortCaps', []))
        logger.debug('SortCaps for %s: %r', uri, sortcaps)
        if '*' in sortcaps:
            return order
        else:
            return list(filter(lambda f: f[1:] in sortcaps, order))
