from __future__ import unicode_literals

import logging
import os

from mopidy import config, exceptions, ext

__version__ = '0.5.0'

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
        import dbus
        try:
            if 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
                bus = dbus.SessionBus()
            else:
                bus = self.__start_bus()
        except Exception as e:
            raise exceptions.ExtensionError(str(e))
        from .dleyna import SERVER_BUS_NAME, SERVER_ROOT_PATH
        try:
            bus.get_object(SERVER_BUS_NAME, SERVER_ROOT_PATH)
        except Exception as e:
            raise exceptions.ExtensionError(str(e))

    def __start_bus(self):
        import dbus
        import subprocess
        logger.info('Starting D-Bus session bus')
        launch = subprocess.Popen('dbus-launch', stdout=subprocess.PIPE)
        for line in launch.stdout:
            name, sep, value = line.partition(b'=')
            if sep:
                logger.debug('dbus-launch output: %s=%s', name, value)
                os.environ[name.strip()] = value.strip()
            else:
                logger.warn('Unexpected dbus-launch output: %s', line)
        launch.wait()
        # FIXME: environment variables ignored by dbus.SessionBus()
        return dbus.bus.BusConnection(os.environ['DBUS_SESSION_BUS_ADDRESS'])
