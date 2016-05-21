from __future__ import absolute_import, unicode_literals

import logging
import time

import pykka

logger = logging.getLogger(__name__)


class Future(pykka.ThreadingFuture):

    Timeout = pykka.Timeout

    def apply(self, func):
        # similar to map(), but always works on single value
        future = self.__class__()
        future.set_get_hook(lambda timeout: func(self.get(timeout)))
        return future

    @classmethod
    def exception(cls, exc_info=None):
        future = cls()
        future.set_exception(exc_info)
        return future

    @classmethod
    def fromdbus(cls, func, *args, **kwargs):
        method = getattr(func, '_method_name', '<unknown>')
        logger.debug('Calling D-Bus method %s%s', method, args)
        future = cls()
        start = time.time()

        def reply(*args):
            logger.debug('%s reply after %.3fs', method, time.time() - start)
            future.set(args[0] if len(args) == 1 else args)

        def error(e):
            logger.debug('%s error after %.3fs', method, time.time() - start)
            future.set_exception(exc_info=(type(e), e, None))

        func(*args, reply_handler=reply, error_handler=error, **kwargs)
        return future

    @classmethod
    def fromvalue(cls, value):
        future = cls()
        future.set(value)
        return future
