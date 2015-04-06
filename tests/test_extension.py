from __future__ import unicode_literals

from mopidy_dleyna import Extension


def test_get_default_config():
    ext = Extension()
    config = ext.get_default_config()
    assert '[dleyna]' in config
    assert 'enabled = true' in config


def test_get_config_schema():
    ext = Extension()
    schema = ext.get_config_schema()
    assert 'enabled' in schema


# TODO Write more tests
