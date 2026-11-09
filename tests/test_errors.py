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
