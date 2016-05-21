from __future__ import unicode_literals

from mopidy.models import Album, Artist, Ref, Track

import pytest

from mopidy_dleyna import translator

BASEURI = 'dleyna://foo'
BASEPATH = '/com/intel/dLeynaServer/server/0'

ALBUM_TYPE = 'container.album.musicAlbum'
ARTIST_TYPE = 'container.person.musicArtist'


def test_album_ref():
    assert translator.ref({
        'DisplayName': 'Foo',
        'URI': BASEURI + '/foo',
        'Type': 'container',
        'TypeEx': ALBUM_TYPE
    }) == Ref.album(uri=BASEURI+'/foo', name='Foo')


def test_artist_ref():
    assert translator.ref({
        'DisplayName': 'Foo',
        'URI': BASEURI + '/foo',
        'Type': 'container',
        'TypeEx': ARTIST_TYPE
    }) == Ref.artist(uri=BASEURI+'/foo', name='Foo')


def test_track_ref():
    assert translator.ref({
        'DisplayName': 'Foo',
        'URI': BASEURI + '/foo',
        'Type': 'music',
    }) == Ref.track(uri=BASEURI+'/foo', name='Foo')


def test_directory_ref():
    assert translator.ref({
        'DisplayName': 'Foo',
        'URI': BASEURI + '/foo',
        'Type': 'container'
    }) == Ref.directory(uri=BASEURI+'/foo', name='Foo')


def test_video_ref():
    with pytest.raises(ValueError):
        translator.ref({
            'DisplayName': 'Foo',
            'URI': BASEURI + '/foo',
            'Type': 'video'
        })


def test_album():
    assert translator.model({
        'DisplayName': 'Foo',
        'URI': BASEURI + '/foo',
        'Type': 'container',
        'TypeEx': ALBUM_TYPE
    }) == Album(uri=BASEURI+'/foo', name='Foo')


def test_artist():
    assert translator.model({
        'DisplayName': 'Foo',
        'URI': BASEURI + '/foo',
        'Type': 'container',
        'TypeEx': ARTIST_TYPE
    }) == Artist(uri=BASEURI+'/foo', name='Foo')


def test_track():
    assert translator.model({
        'DisplayName': 'Foo',
        'Album': 'Bar',
        'URI': BASEURI + '/foo',
        'Type': 'music',
    }) == Track(uri=BASEURI+'/foo', name='Foo', album=Album(name='Bar'))


def test_video():
    with pytest.raises(ValueError):
        translator.model({
            'DisplayName': 'Foo',
            'URI': BASEURI + '/foo',
            'Type': 'video'
        })
