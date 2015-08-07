from __future__ import absolute_import, unicode_literals

from mopidy import backend

from uritools import urisplit


class dLeynaPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        parts = urisplit(uri)
        dleyna = self.backend.dleyna
        server = dleyna.get_server(parts.gethost())
        return dleyna.get_item_url(server['Path'] + parts.getpath())
