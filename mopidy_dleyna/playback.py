from __future__ import absolute_import, unicode_literals

import logging

from mopidy import backend

logger = logging.getLogger(__name__)


class dLeynaPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        # TODO: GetCompatibleResources w/protocol_info
        client = self.backend.client
        try:
            obj = client.properties(uri, client.MEDIA_ITEM_IFACE).get()
        except Exception as e:
            logger.error('Error translating %s: %s', uri, e)
        else:
            return obj['URLs'][0]
