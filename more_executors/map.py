"""Transform the output value of a future."""

from concurrent.futures import Executor

from more_executors._common import _Future

__pdoc__ = {}
__pdoc__['MapExecutor.shutdown'] = None
__pdoc__['MapExecutor.map'] = None


class _MapFuture(_Future):
    def __init__(self, delegate, map_fn):
        super(_MapFuture, self).__init__()
        self._delegate = delegate
        self._map_fn = map_fn
        self._delegate.add_done_callback(self._delegate_resolved)

    def _delegate_resolved(self, delegate):
        assert delegate is self._delegate, \
            "BUG: called with %s, expected %s" % (delegate, self._delegate)

        if delegate.cancelled():
            return

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

    def set_result(self, result):
        with self._me_lock:
            super(_MapFuture, self).set_result(result)
        self._me_invoke_callbacks()

    def set_exception(self, exception):
        with self._me_lock:
            super(_MapFuture, self).set_exception(exception)
        self._me_invoke_callbacks()

    def running(self):
        with self._me_lock:
            if self.done():
                return False
            return self._delegate.running() or self._delegate.done()

    def cancel(self):
        with self._me_lock:
            if self.cancelled():
                return True
            if not self._delegate.cancel():
                return False
            out = super(_MapFuture, self).cancel()
            if out:
                self.set_running_or_notify_cancel()
        if out:
            self._me_invoke_callbacks()
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
