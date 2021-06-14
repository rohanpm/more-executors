from concurrent.futures import Executor
from threading import RLock
import logging

from .wrap import CanCustomizeBind
from .logwrap import LogWrapper


class CancelOnShutdownExecutor(CanCustomizeBind, Executor):
    """An executor which delegates to another executor and cancels all
    futures when the executor is shut down.

    This class is useful in conjunction with executors having custom cancel
    behavior, such as :class:`~more_executors.poll.PollExecutor`.

    .. note::
        From Python 3.9 onwards, the standard
        :meth:`~concurrent.futures.Executor.shutdown` method includes a
        ``cancel_futures`` parameter which can be used to cancel futures
        on shutdown.

        These two approaches of cancelling futures on shutdown have the
        following differences:

        - ``cancel_futures=True`` will only cancel futures which have not
          yet started running.
        - ``CancelOnShutdownExecutor`` will attempt to cancel *all* incomplete
          futures, including those which are running.

        If you're using other executors from this library and you want to
        ensure futures are cancelled on shutdown, ``CancelOnShutdownExecutor``
        should be preferred because several of the executor classes in this
        library do support cancellation of running futures (unlike the executors
        in the standard library).
    """

    def __init__(self, delegate, logger=None):
        """
        Parameters:

            delegate (~concurrent.futures.Executor):
                executor to which callables will be submitted

            logger (~logging.Logger):
                a logger used for messages from this executor
        """
        self._log = LogWrapper(
            logger if logger else logging.getLogger("CancelOnShutdownExecutor")
        )
        self._delegate = delegate
        self._futures = set()
        self._lock = RLock()
        self._shutdown = False

    def shutdown(self, wait=True, **_kwargs):
        """Shut down the executor.

        All futures created by this executor which have not yet been completed
        will have :meth:`~concurrent.futures.Future.cancel` invoked.

        Note that there is no guarantee that the cancel will succeed, and only a single
        attempt is made to cancel any future.
        """
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True
            futures = self._futures.copy()

        for f in futures:
            cancel = f.cancel()
            self._log.debug("Cancel %s: %s", f, cancel)

        self._delegate.shutdown(wait, **_kwargs)

    def submit(self, *args, **kwargs):  # pylint: disable=arguments-differ
        with self._lock:
            if self._shutdown:
                raise RuntimeError("Cannot submit after shutdown")
            future = self._delegate.submit(*args, **kwargs)
            self._futures.add(future)
            future.add_done_callback(self._futures.discard)
        return future
