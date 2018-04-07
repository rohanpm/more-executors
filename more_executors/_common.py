from concurrent.futures import Future
from threading import RLock
import logging

_LOG = logging.getLogger('more_executors._Future')

# This value should be used for any blocking waits likely to be invoked
# from the main thread, where blocking forever is technically appropriate.
#
# The reason for this is that, in Python 2.x, a blocking wait with no
# timeout (such as a thread join) is entirely uninterruptible, always
# retrying on EINTR, which can easily lead to a process not responding
# to anything but SIGKILL.
#
# Providing a timeout value - no matter what it is - causes the wait to
# become interruptible, which is desirable.
#
# This value is an arbitrary choice.  100 years ought to be enough for anyone :)
_MAX_TIMEOUT = 60*60*24*365*100


class _Future(Future):
    # Need to reimplement some of the Future class.
    # We must hold callbacks ourselves and not let the parent class handle them.
    # This is necessary for locking: we need to handle some locking ourselves,
    # but we must NOT have the callbacks invoked while our lock is held.
    # (Note: an alternative would be to access concurrent.futures private variables)
    def __init__(self):
        super(_Future, self).__init__()
        self._me_done_callbacks = []
        self._me_lock = RLock()

    def _me_invoke_callbacks(self):
        for callback in self._me_done_callbacks:
            try:
                callback(self)
            except Exception:
                _LOG.exception('exception calling callback for %r', self)

    def add_done_callback(self, fn):
        # Overrides function from parent; intentionally does not call super,
        # so we own the callbacks ourself
        with self._me_lock:
            if not self.done():
                self._me_done_callbacks.append(fn)
                return
        # Already done -> call it directly
        fn(self)

    def cancel(self):
        with self._me_lock:
            if self.cancelled():
                return True
            if self.done():
                return False
            if not self._me_cancel():
                return False
            out = super(_Future, self).cancel()
            if out:
                self.set_running_or_notify_cancel()
        if out:
            self._me_invoke_callbacks()
        return out

    def _me_cancel(self):
        assert False, 'BUG: override this method in subclasses!'  # pragma: no cover
