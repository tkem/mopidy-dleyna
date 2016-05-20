from __future__ import unicode_literals

import os

from mopidy import config, exceptions, ext

__version__ = '1.1.0'


class Extension(ext.Extension):

    dist_name = 'Mopidy-dLeyna'
    ext_name = 'dleyna'
    version = __version__

    def get_default_config(self):
        return config.read(os.path.join(os.path.dirname(__file__), 'ext.conf'))

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['upnp_browse_limit'] = config.Integer(minimum=0)
        schema['upnp_lookup_limit'] = config.Integer(minimum=0)
        schema['upnp_search_limit'] = config.Integer(minimum=0)
        return schema

    def setup(self, registry):
        from .backend import dLeynaBackend
        registry.add('backend', dLeynaBackend)

    def validate_environment(self):
        try:
            import dbus  # noqa
        except ImportError:
            raise exceptions.ExtensionError('Cannot import dbus')
