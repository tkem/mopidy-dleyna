from __future__ import unicode_literals

import mock

import pytest


@pytest.fixture
def item():
    return {
        'DisplayName': 'Track #1',
        'Type': 'music',
        'URI': 'dleyna://media/1',
        'URLs': ['http://example.com/1.mp3']
    }


def test_translate_uri(backend, item):
    with mock.patch.object(backend, 'client') as m:
        m.properties.return_value.get.return_value = item
        assert backend.playback.translate_uri(item['URI']) == item['URLs'][0]


def test_translate_unknown_uri(backend):
    with mock.patch.object(backend, 'client') as m:
        m.properties.return_value.get.side_effect = Exception('Not Found')
        assert backend.playback.translate_uri('') is None
