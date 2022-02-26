from concurrent.futures import Executor

from .metrics import metrics
from .helpers import ShutdownHelper

try:
    import asyncio
except Exception:  # pylint: disable=broad-except
    pass


class AsyncioExecutor(Executor):
    """An executor which delegates to another executor while converting
    returned futures into instances of :class:`asyncio.Future`.

    Note that since this class produces :mod:`asyncio` rather than :mod:`concurrent.futures`
    future objects, AsyncioExecutor instances themselves cannot be used
    as a delegate executor of other executor instances within this library.

    .. versionadded:: 1.7.0
    """

    def __init__(self, delegate, loop=None, logger=None, name="default"):
        """
        Parameters:

            delegate (~concurrent.futures.Executor):
                executor to which callables will be submitted

            loop (~asyncio.AbstractEventLoop):
                asyncio event loop used to wrap futures; if omitted, the default
                event loop is used.

            logger (~logging.Logger):
                a logger used for messages from this executor

            name (str):
                a name for this executor

        .. versionchanged:: 2.7.0
            Introduced ``name``.
        """
        self._delegate = delegate
        self._loop = loop
        self._name = name
        self._shutdown = ShutdownHelper()
        metrics.EXEC_TOTAL.labels(type="asyncio", executor=self._name).inc()
        metrics.EXEC_INPROGRESS.labels(type="asyncio", executor=self._name).inc()

    def submit(self, *args, **kwargs):  # pylint: disable=arguments-differ
        return self.submit_with_loop(self._loop, *args, **kwargs)

    def submit_with_loop(self, loop, fn, *args, **kwargs):
        """Submit a callable with the specified event loop.

        Parameters:
            loop (~asyncio.AbstractEventLoop):
                asyncio event loop used to wrap futures

            fn (callable):
                callable to be submitted

        Returns:
            asyncio.Future:
                a future for the given callable
        """
        with self._shutdown.ensure_alive():
            if not loop:
                loop = asyncio.get_event_loop()
            future = self._delegate.submit(fn, *args, **kwargs)
            return asyncio.wrap_future(future, loop=loop)

    def shutdown(self, wait=True, **_kwargs):
        if self._shutdown():
            metrics.EXEC_INPROGRESS.labels(type="asyncio", executor=self._name).dec()
            self._delegate.shutdown(wait, **_kwargs)
