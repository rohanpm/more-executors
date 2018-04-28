"""Wrap `concurrent.futures` with `asyncio` futures."""
from concurrent.futures import Executor
import asyncio

__pdoc__ = {}
__pdoc__['AsyncioExecutor.shutdown'] = None
__pdoc__['AsyncioExecutor.map'] = None


class AsyncioExecutor(Executor):
    """An `Executor` which delegates to another `Executor` while converting
    returned futures into
    [`asyncio` futures](https://docs.python.org/3/library/asyncio-task.html).

    Note that since this class produces `asyncio` rather than `concurrent.futures`
    future objects, `AsyncioExecutor` instances themselves cannot be used
    as a delegate executor of other executor instances within this library.

    *Since version 1.7.0*
    """
    def __init__(self, delegate, loop=None, logger=None):
        """Create a new executor.

        - `delegate`: `Executor` instance to which callables will be submitted
        - `loop`: `asyncio` event loop used to wrap futures; if omitted, the default
                  event loop is used.
        - `logger`: a `Logger` used for messages from this executor
        """
        self._delegate = delegate
        self._loop = loop

    def submit(self, fn, *args, **kwargs):
        """Submit a callable with this executor's default event loop.

        Returns an `asyncio` future."""
        return self.submit_with_loop(self._loop, fn, *args, **kwargs)

    def submit_with_loop(self, loop, fn, *args, **kwargs):
        """Submit a callable with the specified event loop.

        Returns an `asyncio` future."""
        if not loop:
            loop = asyncio.get_event_loop()
        future = self._delegate.submit(fn, *args, **kwargs)
        return asyncio.wrap_future(future, loop=loop)

    def shutdown(self, wait=True):
        self._delegate.shutdown(wait)
