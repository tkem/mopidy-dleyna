from __future__ import unicode_literals

import dbus
import logging

from mopidy import backend
from mopidy.models import Ref

logger = logging.getLogger(__name__)


class dLeynaLibraryProvider(backend.LibraryProvider):

    root_directory = Ref.directory(
        uri='dleyna:',
        name='DLNA Servers'
    )

    def __init__(self, config, backend):
        super(dLeynaLibraryProvider, self).__init__(backend)
        bus = dbus.SessionBus()
        self.__manager = dbus.Interface(
            bus.get_object(
                'com.intel.dleyna-server',
                '/com/intel/dLeynaServer'
            ),
            'com.intel.dLeynaServer.Manager'
        )
        self._propsIF = dbus.Interface(bus.get_object(
						'com.intel.dleyna-server',
						'/com/intel/dLeynaServer'),
				       'org.freedesktop.DBus.Properties')

        logger.info('manager %r' % self.__manager)

    def browse(self, uri):
        bus = dbus.SessionBus()

        refs = []
        if uri == 'dleyna:':
            for path in self.__manager.GetServers():
                logger.info('server: %r' % path)
                try:
                    props = dbus.Interface(
                        bus.get_object(
                            'com.intel.dleyna-server',
                            path
                        ),
                        'org.freedesktop.DBus.Properties'
                    )
                    try:
                        name = props.Get('', 'FriendlyName')
                    except Exception:
                        name = props.Get('', 'DisplayName')
                    refs.append(Ref.directory(name=name, uri='dleyna:'+path))
                except dbus.exceptions.DBusException as e:
                    logger.error('error %r' % e)
        return refs
