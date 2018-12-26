from concurrent.futures import Executor
import asyncio


class AsyncioExecutor(Executor):
    """An executor which delegates to another executor while converting
    returned futures into instances of :class:`asyncio.Future`.

    Note that since this class produces :mod:`asyncio` rather than :mod:`concurrent.futures`
    future objects, AsyncioExecutor instances themselves cannot be used
    as a delegate executor of other executor instances within this library.

    .. versionadded:: 1.7.0
    """
    def __init__(self, delegate, loop=None, logger=None):
        """
        Parameters:

            delegate (~concurrent.futures.Executor):
                executor to which callables will be submitted

            loop (~asyncio.AbstractEventLoop):
                asyncio event loop used to wrap futures; if omitted, the default
                event loop is used.

            logger (~logging.Logger):
                a logger used for messages from this executor
        """
        self._delegate = delegate
        self._loop = loop

    def submit(self, fn, *args, **kwargs):
        return self.submit_with_loop(self._loop, fn, *args, **kwargs)

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
        if not loop:
            loop = asyncio.get_event_loop()
        future = self._delegate.submit(fn, *args, **kwargs)
        return asyncio.wrap_future(future, loop=loop)

    def shutdown(self, wait=True):
        self._delegate.shutdown(wait)
