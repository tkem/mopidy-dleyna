from unittest import mock

import pytest
from mopidy import models

from mopidy_dleyna.util import Future

SERVER = {
    "FriendlyName": "Media Server",
    "DisplayName": "Media",
    "SearchCaps": ["DisplayName", "Path"],
    "Path": "/com/intel/dLeynaServer/server/0",
    "URI": "dleyna://media",
}

ERRORS = [
    LookupError("Unknown media server UDN media"),
    RuntimeError("org.freedesktop.DBus.Error.NoReply"),
]


def error(e):
    return mock.Mock(side_effect=lambda *args, **kwargs: Future.exception(e))


@pytest.mark.parametrize("e", ERRORS)
def test_browse_root_error(backend, e):
    with mock.patch.object(backend, "client") as m:
        m.servers = error(e)
        assert backend.library.browse(backend.library.root_directory.uri) == []


@pytest.mark.parametrize("e", ERRORS)
def test_browse_error(backend, e):
    with mock.patch.object(backend, "client") as m:
        m.properties = error(e)
        assert backend.library.browse("dleyna://media/1") == []


@pytest.mark.parametrize("e", ERRORS)
def test_lookup_error(backend, e):
    with mock.patch.object(backend, "client") as m:
        m.properties = error(e)
        assert backend.library.lookup("dleyna://media/11") == []


@pytest.mark.parametrize("e", ERRORS)
def test_get_images_server_error(backend, e):
    with mock.patch.object(backend, "client") as m:
        m.server = error(e)
        assert backend.library.get_images(["dleyna://media/11"]) == {}


@pytest.mark.parametrize("e", ERRORS)
def test_get_images_search_error(backend, e):
    with mock.patch.object(backend, "client") as m:
        m.server.return_value = Future.fromvalue(SERVER)
        m.search = error(e)
        assert backend.library.get_images(["dleyna://media/11"]) == {}


@pytest.mark.parametrize("e", ERRORS)
def test_search_server_error(backend, e):
    with mock.patch.object(backend, "client") as m:
        m.servers.return_value = Future.fromvalue([SERVER])
        m.server = error(e)
        assert backend.library.search({"any": ["foo"]}) is None


@pytest.mark.parametrize("e", ERRORS)
def test_search_error(backend, e):
    with mock.patch.object(backend, "client") as m:
        m.servers.return_value = Future.fromvalue([SERVER])
        m.server.return_value = Future.fromvalue(SERVER)
        m.search = error(e)
        assert backend.library.search({"any": ["foo"]}) == models.SearchResult()


@pytest.mark.parametrize("e", ERRORS)
def test_search_servers_error(backend, e):
    with mock.patch.object(backend, "client") as m:
        m.servers = error(e)
        assert backend.library.search({"any": ["foo"]}) is None


GOOD = dict(SERVER, URI="dleyna://good", FriendlyName="Good")
BAD = dict(SERVER, URI="dleyna://bad", FriendlyName="Bad")


def by_server(results):
    # dispatch client calls on their first argument, the server or object URI
    def call(uri, *args, **kwargs):
        result = results[uri.split("/")[2]]
        if isinstance(result, Exception):
            return Future.exception(result)
        return Future.fromvalue(result)

    return mock.Mock(side_effect=call)


@pytest.mark.parametrize("e", ERRORS)
@pytest.mark.parametrize("fail", ["server", "search"])
def test_get_images_mixed_servers(backend, e, fail):
    item = {"Type": "music", "AlbumArtURL": "http://x/1.jpg", "URI": "dleyna://good/1"}
    with mock.patch.object(backend, "client") as m:
        m.server = by_server({"good": GOOD, "bad": e if fail == "server" else BAD})
        m.search = by_server({"good": [[item], False], "bad": e})
        assert backend.library.get_images(["dleyna://good/1", "dleyna://bad/1"]) == {
            "dleyna://good/1": (models.Image(uri="http://x/1.jpg"),)
        }


@pytest.mark.parametrize("e", ERRORS)
@pytest.mark.parametrize("fail", ["server", "search"])
def test_search_mixed_servers(backend, e, fail):
    track = {"DisplayName": "Track", "Type": "music", "URI": "dleyna://good/1"}
    with mock.patch.object(backend, "client") as m:
        m.servers.return_value = Future.fromvalue([GOOD, BAD])
        m.server = by_server({"good": GOOD, "bad": e if fail == "server" else BAD})
        m.search = by_server({"good": [[track], False], "bad": e})
        assert backend.library.search({"any": ["foo"]}) == models.SearchResult(
            tracks=[models.Track(name="Track", uri="dleyna://good/1")]
        )
