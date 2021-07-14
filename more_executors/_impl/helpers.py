import logging
from functools import wraps
from threading import Lock
from contextlib import contextmanager

from .logwrap import LogWrapper

LOG = LogWrapper(logging.getLogger(__name__))


def executor_loop(fn):
    @wraps(fn)
    def out(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except RuntimeError as error:
            if "cannot schedule new futures after" in str(error):
                LOG.debug("Ignoring error due to interpreter shutdown", exc_info=1)
                return
            raise

    return out


class ShutdownHelper(object):
    def __init__(self):
        self._lock = Lock()
        self.is_shutdown = False

    @contextmanager
    def ensure_alive(self):
        with self._lock:
            if self.is_shutdown:
                raise RuntimeError("cannot schedule new futures after shutdown")
            yield

    def __call__(self):
        # Ensure shut down, return True if newly shutdown or
        # False if already shutdown
        with self._lock:
            if self.is_shutdown:
                return False
            self.is_shutdown = True
            return True
