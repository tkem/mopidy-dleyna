from __future__ import unicode_literals

import mock

from mopidy import models

import pytest

from mopidy_dleyna.util import Future


@pytest.fixture
def container():
    return {
        'DisplayName': 'Album #1',
        'Type': 'container',
        'TypeEx': 'container.album.musicAlbum',
        'URI': 'dleyna://media/1'
    }


@pytest.fixture
def items():
    return [
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


def test_lookup_root(backend):
    assert backend.library.lookup(backend.library.root_directory.uri) == []


def test_lookup_item(backend, items):
    with mock.patch.object(backend, 'client') as m:
        m.properties.return_value = Future.fromvalue(items[0])
        assert backend.library.lookup(items[0]['URI']) == [
            models.Track(name='Track #1', uri='dleyna://media/11')
        ]


def test_lookup_container(backend, container, items):
    with mock.patch.object(backend, 'client') as m:
        m.properties.return_value = Future.fromvalue(container)
        m.search.return_value = Future.fromvalue(items)
        assert backend.library.lookup(container['URI']) == [
            models.Track(name='Track #1', uri='dleyna://media/11'),
            models.Track(name='Track #2', uri='dleyna://media/12')
        ]
