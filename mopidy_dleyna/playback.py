from __future__ import absolute_import, unicode_literals

import logging

from mopidy import backend

logger = logging.getLogger(__name__)


class dLeynaPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        dleyna = self.backend.dleyna
        try:
            obj = dleyna.properties(uri, dleyna.MEDIA_ITEM_IFACE).get()
        except Exception as e:
            logger.error('Error translating %s: %s', uri, e)
            return None
        else:
            # TODO: GetCompatibleResources w/protocol_info
            return obj['URLs'][0]
