from __future__ import absolute_import, unicode_literals

from mopidy import backend


class dLeynaPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        dleyna = self.backend.dleyna
        # TODO: GetCompatibleResources w/protocol_info
        future = dleyna.properties(uri, dleyna.MEDIA_ITEM_IFACE)
        return future.get()['URLs'][0]
