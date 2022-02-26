from concurrent.futures import Executor
from threading import RLock
import logging

from .wrap import CanCustomizeBind
from .logwrap import LogWrapper
from .metrics import metrics
from .helpers import ShutdownHelper


class CancelOnShutdownExecutor(CanCustomizeBind, Executor):
    """An executor which delegates to another executor and cancels all
    futures when the executor is shut down.

    This class is useful in conjunction with executors having custom cancel
    behavior, such as :class:`~more_executors.PollExecutor`.

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

    def __init__(self, delegate, logger=None, name="default"):
        """
        Parameters:

            delegate (~concurrent.futures.Executor):
                executor to which callables will be submitted

            logger (~logging.Logger):
                a logger used for messages from this executor

            name (str):
                a name for this executor

        .. versionchanged:: 2.7.0
            Introduced ``name``.
        """
        self._log = LogWrapper(
            logger if logger else logging.getLogger("CancelOnShutdownExecutor")
        )
        self._name = name
        self._delegate = delegate
        self._futures = set()
        self._lock = RLock()
        self._shutdown = ShutdownHelper()
        metrics.EXEC_TOTAL.labels(type="cancel_on_shutdown", executor=self._name).inc()
        metrics.EXEC_INPROGRESS.labels(
            type="cancel_on_shutdown", executor=self._name
        ).inc()

    def shutdown(self, wait=True, **_kwargs):
        """Shut down the executor.

        All futures created by this executor which have not yet been completed
        will have :meth:`~concurrent.futures.Future.cancel` invoked.

        Note that there is no guarantee that the cancel will succeed, and only a single
        attempt is made to cancel any future.
        """
        with self._lock:
            if not self._shutdown():
                return
            metrics.EXEC_INPROGRESS.labels(
                type="cancel_on_shutdown", executor=self._name
            ).dec()
            futures = self._futures.copy()

        for f in futures:
            cancel = f.cancel()
            self._log.debug("Cancel %s: %s", f, cancel)
            if cancel:
                metrics.SHUTDOWN_CANCEL.labels(executor=self._name).inc()

        self._delegate.shutdown(wait, **_kwargs)

    def submit(self, *args, **kwargs):  # pylint: disable=arguments-differ
        with self._shutdown.ensure_alive():
            with self._lock:
                future = self._delegate.submit(*args, **kwargs)
                self._futures.add(future)
                future.add_done_callback(self._futures.discard)
            return future
