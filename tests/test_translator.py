import pytest

from mopidy.models import Album, Artist, Ref, Track
from mopidy_dleyna import translator

BASEURI = "dleyna://foo"
BASEPATH = "/com/intel/dLeynaServer/server/0"

ALBUM_TYPE = "container.album.musicAlbum"
ARTIST_TYPE = "container.person.musicArtist"
PLAYLIST_TYPE = "container.playlistContainer"
AUDIO_BOOK_TYPE = "item.audioItem.audioBook"
AUDIO_BROADCAST_TYPE = "item.audioItem.audioBroadcast"


def test_album_ref():
    assert translator.ref(
        {
            "DisplayName": "Foo",
            "URI": BASEURI + "/foo",
            "Type": "container",
            "TypeEx": ALBUM_TYPE,
        }
    ) == Ref.album(uri=BASEURI + "/foo", name="Foo")


def test_artist_ref():
    assert translator.ref(
        {
            "DisplayName": "Foo",
            "URI": BASEURI + "/foo",
            "Type": "container",
            "TypeEx": ARTIST_TYPE,
        }
    ) == Ref.artist(uri=BASEURI + "/foo", name="Foo")


def test_music_ref():
    assert translator.ref(
        {"DisplayName": "Foo", "URI": BASEURI + "/foo", "Type": "music"}
    ) == Ref.track(uri=BASEURI + "/foo", name="Foo")


def test_audio_book_ref():
    assert translator.ref(
        {
            "DisplayName": "Foo",
            "URI": BASEURI + "/foo",
            "Type": "audio",
            "TypeEx": AUDIO_BOOK_TYPE,
        }
    ) == Ref.track(uri=BASEURI + "/foo", name="Foo")


def test_audio_broadcast_ref():
    assert translator.ref(
        {
            "DisplayName": "Foo",
            "URI": BASEURI + "/foo",
            "Type": "audio",
            "TypeEx": AUDIO_BROADCAST_TYPE,
        }
    ) == Ref.track(uri=BASEURI + "/foo", name="Foo")


def test_container_ref():
    assert translator.ref(
        {"DisplayName": "Foo", "URI": BASEURI + "/foo", "Type": "container"}
    ) == Ref.directory(uri=BASEURI + "/foo", name="Foo")


def test_video_ref():
    with pytest.raises(ValueError):
        translator.ref(
            {"DisplayName": "Foo", "URI": BASEURI + "/foo", "Type": "video"}
        )


def test_album():
    assert translator.model(
        {
            "DisplayName": "Foo",
            "URI": BASEURI + "/foo",
            "Type": "container",
            "TypeEx": ALBUM_TYPE,
        }
    ) == Album(uri=BASEURI + "/foo", name="Foo")


def test_artist():
    assert translator.model(
        {
            "DisplayName": "Foo",
            "URI": BASEURI + "/foo",
            "Type": "container",
            "TypeEx": ARTIST_TYPE,
        }
    ) == Artist(uri=BASEURI + "/foo", name="Foo")


def test_playlist():
    assert translator.ref(
        {
            "DisplayName": "Foo",
            "URI": BASEURI + "/foo",
            "Type": "container",
            "TypeEx": PLAYLIST_TYPE,
        }
    ) == Ref.directory(uri=BASEURI + "/foo", name="Foo")


def test_track():
    assert translator.model(
        {
            "DisplayName": "Foo",
            "Album": "Bar",
            "URI": BASEURI + "/foo",
            "Type": "music",
        }
    ) == Track(uri=BASEURI + "/foo", name="Foo", album=Album(name="Bar"))


def test_audio_book():
    assert translator.model(
        {
            "DisplayName": "Foo",
            "URI": BASEURI + "/foo",
            "Type": "audio",
            "TypeEx": AUDIO_BOOK_TYPE,
        }
    ) == Track(uri=BASEURI + "/foo", name="Foo")


def test_audio_broadcast():
    assert translator.model(
        {
            "DisplayName": "Foo",
            "URI": BASEURI + "/foo",
            "Type": "audio",
            "TypeEx": AUDIO_BROADCAST_TYPE,
        }
    ) == Track(uri=BASEURI + "/foo", name="Foo")


def test_video():
    with pytest.raises(ValueError):
        translator.model(
            {"DisplayName": "Foo", "URI": BASEURI + "/foo", "Type": "video"}
        )
