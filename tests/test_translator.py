from __future__ import unicode_literals

from mopidy.models import Album, Artist, Ref, Track

from mopidy_dleyna import translator

BASEURI = 'dleyna://foo'
BASEPATH = '/com/intel/dLeynaServer/server/0'


def test_album_ref():
    assert translator.ref(BASEURI, {
        'DisplayName': 'Foo',
        'Path': BASEPATH + '/foo',
        'Type': 'container',
        'TypeEx': translator.ALBUM_TYPE
    }) == Ref.album(uri=BASEURI+'/foo', name='Foo')


def test_artist_ref():
    assert translator.ref(BASEURI, {
        'DisplayName': 'Foo',
        'Path': BASEPATH + '/foo',
        'Type': 'container',
        'TypeEx': translator.ARTIST_TYPE
    }) == Ref.artist(uri=BASEURI+'/foo', name='Foo')


def test_track_ref():
    assert translator.ref(BASEURI, {
        'DisplayName': 'Foo',
        'Path': BASEPATH + '/foo',
        'Type': 'music',
    }) == Ref.track(uri=BASEURI+'/foo', name='Foo')


def test_directory_ref():
    assert translator.ref(BASEURI, {
        'DisplayName': 'Foo',
        'Path': BASEPATH + '/foo',
        'Type': 'container'
    }) == Ref.directory(uri=BASEURI+'/foo', name='Foo')


def test_album():
    assert translator.model(BASEURI, {
        'DisplayName': 'Foo',
        'Path': BASEPATH + '/foo',
        'Type': 'container',
        'TypeEx': translator.ALBUM_TYPE
    }) == Album(uri=BASEURI+'/foo', name='Foo')


def test_artist():
    assert translator.model(BASEURI, {
        'DisplayName': 'Foo',
        'Path': BASEPATH + '/foo',
        'Type': 'container',
        'TypeEx': translator.ARTIST_TYPE
    }) == Artist(uri=BASEURI+'/foo', name='Foo')


def test_track():
    assert translator.model(BASEURI, {
        'DisplayName': 'Foo',
        'Path': BASEPATH + '/foo',
        'Type': 'music',
    }) == Track(uri=BASEURI+'/foo', name='Foo')
