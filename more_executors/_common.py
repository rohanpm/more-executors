from concurrent.futures import Future
from threading import RLock
import logging

_LOG = logging.getLogger('more_executors._Future')


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
