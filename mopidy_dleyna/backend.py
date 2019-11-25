import errno
import logging
import os
import os.path
import re
import signal
import stat
import subprocess

import pykka

from mopidy import backend, exceptions

from . import Extension
from .client import dLeynaClient
from .library import dLeynaLibraryProvider
from .playback import dLeynaPlaybackProvider

DBUS_SESSION_BUS_RE = re.compile(
    r"""
^(?:DBUS_SESSION_BUS_ADDRESS=)?(.*)\n
^(?:DBUS_SESSION_BUS_PID=)?(\d+)$
""",
    re.MULTILINE | re.VERBOSE,
)

logger = logging.getLogger(__name__)


class dLeynaBackend(pykka.ThreadingActor, backend.Backend):

    uri_schemes = [Extension.ext_name]

    __dbus_pid = None

    def __init__(self, config, audio):
        super().__init__()
        try:
            if self.__have_session_bus():
                self.client = dLeynaClient()
            else:
                command = config[Extension.ext_name]["dbus_start_session"]
                address, self.__dbus_pid = self.__start_session_bus(command)
                self.client = dLeynaClient(address)
        except Exception as e:
            logger.error("Error starting %s: %s", Extension.dist_name, e)
            # TODO: clean way to bail out late?
            raise exceptions.ExtensionError("Error starting dLeyna client")
        self.library = dLeynaLibraryProvider(self, config)
        self.playback = dLeynaPlaybackProvider(audio, self)

    def on_stop(self):
        if self.__dbus_pid is not None:
            self.__stop_session_bus(self.__dbus_pid)

    def __have_session_bus(self):
        if "DBUS_SESSION_BUS_ADDRESS" in os.environ:
            return True
        if "XDG_RUNTIME_DIR" not in os.environ:
            return False
        try:
            st = os.stat(os.path.expandvars("$XDG_RUNTIME_DIR/bus"))
        except OSError:
            return False
        else:
            return stat.S_ISSOCK(st.st_mode) and st.st_uid == os.geteuid()

    def __start_session_bus(self, command):
        logger.info("Starting %s D-Bus daemon", Extension.dist_name)
        out = subprocess.check_output(command.split(), universal_newlines=True)
        logger.debug('Running "%s" returned:\n%s', command, out)
        match = DBUS_SESSION_BUS_RE.search(out)
        if not match:
            raise ValueError(f"{command} returned invalid output: {out}")
        else:
            return str(match.group(1)), int(match.group(2))

    def __stop_session_bus(self, pid):
        logger.error("Stopping %s D-Bus daemon (%d)", Extension.dist_name, pid)
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise
        logger.debug("Stopped %s D-Bus daemon", Extension.dist_name)
