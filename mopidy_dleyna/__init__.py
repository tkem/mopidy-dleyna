from __future__ import unicode_literals

import os

from mopidy import config, exceptions, ext

__version__ = '0.5.2'


class Extension(ext.Extension):

    dist_name = 'Mopidy-dLeyna'
    ext_name = 'dleyna'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        return schema

    def setup(self, registry):
        from .backend import dLeynaBackend
        registry.add('backend', dLeynaBackend)

    def validate_environment(self):
        # TODO: dbus requirement?
        try:
            import dbus  # noqa
        except ImportError:
            raise exceptions.ExtensionError('Cannot import dbus')
