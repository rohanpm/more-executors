"""Create futures with a default timeout."""
from concurrent.futures import Executor

from more_executors.map import _MapFuture

__pdoc__ = {}
__pdoc__['TimeoutExecutor.map'] = None
__pdoc__['TimeoutExecutor.shutdown'] = None
__pdoc__['TimeoutExecutor.submit'] = None


class _TimeoutFuture(_MapFuture):
    def __init__(self, delegate, timeout):
        super(_TimeoutFuture, self).__init__(delegate, lambda x: x)
        self._timeout = timeout

    def result(self, timeout=None):
        if timeout is None:
            timeout = self._timeout
        return super(_TimeoutFuture, self).result(timeout)

    def exception(self, timeout=None):
        if timeout is None:
            timeout = self._timeout
        return super(_TimeoutFuture, self).exception(timeout)


class TimeoutExecutor(Executor):
    """An `Executor` which delegates to another `Executor` while adding
    default timeouts to each returned future.

    Note that the default timeouts only apply to the `future.result()` and
    `future.exception()` methods.  Other methods of waiting on futures,
    such as `concurrent.futures.wait()`, will not be affected.

    *Since version 1.6.0*
    """
    def __init__(self, delegate, timeout):
        """Create a new executor.

        - `delegate`: the delegate executor to which callables are submitted.
        - `timeout`: the default timeout applied to any calls to `future.result()`
                     or `future.exception()`, where a timeout has not been provided.
        """
        self._delegate = delegate
        self._timeout = timeout

    def submit(self, fn, *args, **kwargs):
        future = self._delegate.submit(fn, *args, **kwargs)
        return _TimeoutFuture(future, self._timeout)

    def shutdown(self, wait=True):
        self._delegate.shutdown(wait)
