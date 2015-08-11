from __future__ import absolute_import, unicode_literals

from mopidy import backend

from uritools import urisplit


class dLeynaPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        parts = urisplit(uri)
        dleyna = self.backend.dleyna
        server = dleyna.server(parts.gethost()).get()
        path = server['Path'] + parts.getpath()
        # TODO: single prop, MEDIA_ITEM_IFACE, compatible resources...
        future = dleyna.properties(path)
        return future.get()['URLs'][0]
