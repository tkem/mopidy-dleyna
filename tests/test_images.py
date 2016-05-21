from __future__ import unicode_literals

import mock

from mopidy import models

import pytest

from mopidy_dleyna.util import Future


@pytest.fixture
def server():
    return {
        'FriendlyName': 'Media Server',
        'DisplayName': 'Media',
        'SearchCaps': ['DisplayName', 'Path'],
        'Path': '/com/intel/dLeynaServer/server/0',
        'URI': 'dleyna://media'
    }


@pytest.fixture
def items():
    return [
        {
            'DisplayName': 'Track #1',
            'Type': 'music',
            'AlbumArtURL': 'http:://example.com/1.jpg',
            'URI': 'dleyna://media/1'
        },
        {
            'DisplayName': 'Track #2',
            'Type': 'audio',
            'URI': 'dleyna://media/2'
        }
    ]


def test_images(backend, server, items):
    with mock.patch.object(backend, 'client') as m:
        m.servers.return_value = Future.fromvalue([server])
        m.server.return_value = Future.fromvalue(server)
        m.search.return_value = Future.fromvalue(items)
        assert backend.library.get_images(item['URI'] for item in items) == {
            items[0]['URI']: (models.Image(uri=items[0]['AlbumArtURL']),),
            items[1]['URI']: tuple()
        }
