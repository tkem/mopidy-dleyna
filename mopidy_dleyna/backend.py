from __future__ import unicode_literals

import pykka

from mopidy import backend

from . import Extension
from .library import dLeynaLibraryProvider


class dLeynaBackend(pykka.ThreadingActor, backend.Backend):

    uri_schemes = [Extension.ext_name]

    def __init__(self, config, audio):
        super(dLeynaBackend, self).__init__()
        self.library = dLeynaLibraryProvider(config, self)
