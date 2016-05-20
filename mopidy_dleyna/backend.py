from __future__ import absolute_import, unicode_literals

import errno
import logging
import os
import signal
import subprocess

from mopidy import backend, exceptions

import pykka

from . import Extension
from .client import dLeynaClient
from .library import dLeynaLibraryProvider
from .playback import dLeynaPlaybackProvider

DBUS_SESSION_BUS_ADDRESS = 'DBUS_SESSION_BUS_ADDRESS'
DBUS_SESSION_BUS_PID = 'DBUS_SESSION_BUS_PID'

logger = logging.getLogger(__name__)


class dLeynaBackend(pykka.ThreadingActor, backend.Backend):

    uri_schemes = [Extension.ext_name]

    __dbus_pid = None

    def __init__(self, config, audio):
        super(dLeynaBackend, self).__init__()
        try:
            if DBUS_SESSION_BUS_ADDRESS in os.environ:
                self.client = dLeynaClient()
            else:
                env = self.__start_dbus()
                self.__dbus_pid = int(env[DBUS_SESSION_BUS_PID])
                self.client = dLeynaClient(str(env[DBUS_SESSION_BUS_ADDRESS]))
        except Exception as e:
            logger.error('Error starting %s: %s', Extension.dist_name, e)
            # TODO: clean way to bail out late?
            raise exceptions.ExtensionError('Error starting dLeyna client')
        self.library = dLeynaLibraryProvider(self, config)
        self.playback = dLeynaPlaybackProvider(audio, self)

    def on_stop(self):
        if self.__dbus_pid is not None:
            self.__stop_dbus(self.__dbus_pid)

    def __start_dbus(self):
        logger.info('Starting %s D-Bus daemon', Extension.dist_name)
        out = subprocess.check_output(['dbus-launch'], universal_newlines=True)
        logger.debug('%s D-Bus environment:\n%s', Extension.dist_name, out)
        return dict(line.split('=', 1) for line in out.splitlines())

    def __stop_dbus(self, pid):
        logger.info('Stopping %s D-Bus daemon', Extension.dist_name)
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise
        logger.debug('Stopped %s D-Bus daemon', Extension.dist_name)
