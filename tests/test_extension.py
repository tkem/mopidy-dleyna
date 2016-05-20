from __future__ import unicode_literals

from mopidy_dleyna import Extension


def test_get_default_config():
    config = Extension().get_default_config()
    assert '[' + Extension.ext_name + ']' in config
    assert 'enabled = true' in config


def test_get_config_schema():
    schema = Extension().get_config_schema()
    assert 'upnp_browse_limit' in schema
    assert 'upnp_lookup_limit' in schema
    assert 'upnp_search_limit' in schema
