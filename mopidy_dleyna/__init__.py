from __future__ import unicode_literals

import logging
import os

from mopidy import config, exceptions, ext

__version__ = '0.3.1'

logger = logging.getLogger(__name__)


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
        try:
            import dbus
        except ImportError as e:
            raise exceptions.ExtensionError('dbus library not found', e)
        try:
            bus = dbus.SessionBus()
        except Exception as e:
            raise exceptions.ExtensionError('cannot create session bus', e)
        try:
            from .dleyna import SERVER_BUS_NAME, SERVER_ROOT_PATH
            obj = bus.get_object(SERVER_BUS_NAME, SERVER_ROOT_PATH)
        except Exception as e:
            raise exceptions.ExtensionError('cannot access dleyna-server', e)
        try:
            from .dleyna import SERVER_MANAGER_IFACE
            mgr = dbus.Interface(obj, SERVER_MANAGER_IFACE)
        except Exception as e:
            raise exceptions.ExtensionError('cannot access server manager', e)
        logger.info('%s/dleyna-server %s', self.dist_name, mgr.GetVersion())
