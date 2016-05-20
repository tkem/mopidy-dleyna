from __future__ import unicode_literals

import mock

from mopidy import models

import pytest


@pytest.fixture
def server():
    return {
        'FriendlyName': 'Media Server',
        'DisplayName': 'Media',
        'SearchCaps': ['DisplayName'],
        'URI': 'dleyna://media'
    }


@pytest.fixture
def result():
    return [
        {
            'DisplayName': 'Album #1',
            'Type': 'container',
            'TypeEx': 'container.album.musicAlbum',
            'URI': 'dleyna://media/1'
        },
        {
            'DisplayName': 'Track #1',
            'Type': 'music',
            'URI': 'dleyna://media/11'
        },
        {
            'DisplayName': 'Track #2',
            'Type': 'audio',
            'URI': 'dleyna://media/12'
        }
    ]


def test_search(backend, server, result):
    with mock.patch.object(backend, 'client') as m:
        m.servers.return_value.get.return_value = [server]
        m.server.return_value.get.return_value = server
        m.search.return_value.get.return_value = result
        assert backend.library.search({'any': ['foo']}) == models.SearchResult(
            uri='dleyna:?any=foo',
            albums=[
                models.Album(name='Album #1', uri='dleyna://media/1')
            ],
            tracks=[
                models.Track(name='Track #1', uri='dleyna://media/11'),
                models.Track(name='Track #2', uri='dleyna://media/12')
            ]
        )
