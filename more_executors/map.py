"""Transform the output value of a future."""

from threading import RLock
from concurrent.futures import Executor, Future

__pdoc__ = {}
__pdoc__['MapExecutor.shutdown'] = None
__pdoc__['MapExecutor.map'] = None


class _MapFuture(Future):
    def __init__(self, delegate, map_fn):
        super(_MapFuture, self).__init__()
        self._delegate = delegate
        self._map_fn = map_fn
        self._delegate.add_done_callback(self._delegate_resolved)
        self._me_lock = RLock()

    def _delegate_resolved(self, delegate):
        assert delegate is self._delegate, \
            "BUG: called with %s, expected %s" % (delegate, self._delegate)

        ex = delegate.exception()
        if not ex:
            result = delegate.result()
            try:
                result = self._map_fn(result)
            except Exception as map_ex:
                ex = map_ex
                result = None

        if ex:
            self.set_exception(ex)
        else:
            self.set_result(result)

    def running(self):
        return self._delegate.running()

    def done(self):
        return self._delegate.done()

    def cancel(self):
        with self._me_lock:
            if self.cancelled():
                return True
            if not self._delegate.cancel():
                return False
            out = super(_MapFuture, self).cancel()
            if out:
                self.set_running_or_notify_cancel()
        return out


class MapExecutor(Executor):
    """An `Executor` which delegates to another `Executor` while mapping
    output values through a given function.
    """

    def __init__(self, delegate, fn):
        """Create a new executor.

        - `delegate`: `Executor` instance to which callables will be submitted
        - `fn`: a callable applied to transform returned values
        """
        self._delegate = delegate
        self._fn = fn

    def shutdown(self, wait=True):
        self._delegate.shutdown(wait)

    def submit(self, fn, *args, **kwargs):
        """Submit a callable.

        The returned `Future` will have its output value transformed by the
        map function passed to this executor.  If that map function raises
        an exception, the future will fail with that exception."""
        inner_f = self._delegate.submit(fn, *args, **kwargs)
        return _MapFuture(inner_f, self._fn)
