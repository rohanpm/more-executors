"""Cancel futures when executor is shut down."""
from concurrent.futures import Executor
from threading import RLock
import logging

__pdoc__ = {}
__pdoc__['CancelOnShutdownExecutor.submit'] = None
__pdoc__['CancelOnShutdownExecutor.map'] = None

_LOG = logging.getLogger('CancelOnShutdownExecutor')


class CancelOnShutdownExecutor(Executor):
    """An `Executor` which delegates to another `Executor` and cancels all
    futures when the executor is shut down.

    This class is useful in conjunction with executors having custom cancel
    behavior, such as `more_executors.poll.PollExecutor`.
    """

    def __init__(self, delegate):
        """Create a new executor.

        - `delegate`: `Executor` instance to which callables will be submitted
        """
        self._delegate = delegate
        self._futures = set()
        self._lock = RLock()
        self._shutdown = False

    def shutdown(self, wait=True):
        """Shut down the executor.

        All futures created by this executor which have not yet been completed
        will have `cancel` invoked.  Note that there is no guarantee that the
        cancel will succeed.
        """
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True

            for f in self._futures.copy():
                cancel = f.cancel()
                _LOG.debug("Cancel %s: %s", f, cancel)

            self._delegate.shutdown(wait)

    def submit(self, fn, *args, **kwargs):
        with self._lock:
            if self._shutdown:
                raise RuntimeError('Cannot submit after shutdown')
            future = self._delegate.submit(fn, *args, **kwargs)
            self._futures.add(future)
            future.add_done_callback(self._futures.discard)
        return future
