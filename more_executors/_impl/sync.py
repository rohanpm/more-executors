from concurrent.futures import Executor, Future

from .common import copy_exception
from .wrap import CanCustomizeBind
from .metrics import metrics, track_future
from .helpers import ShutdownHelper


class SyncExecutor(CanCustomizeBind, Executor):
    """An executor which immediately invokes all submitted callables."""

    def __init__(self, logger=None, name="default"):
        """
        Parameters:
            logger (~logging.Logger):
                a logger used for messages from this executor
            name (str):
                a name for this executor

        .. versionchanged:: 2.7.0
            Introduced ``name``.
        """
        super(SyncExecutor, self).__init__()
        self._name = name
        self._shutdown = ShutdownHelper()
        metrics.EXEC_TOTAL.labels(type="sync", executor=self._name).inc()
        metrics.EXEC_INPROGRESS.labels(type="sync", executor=self._name).inc()

    def shutdown(self, wait=True, **_kwargs):
        if self._shutdown():
            super(SyncExecutor, self).shutdown(wait, **_kwargs)
            metrics.EXEC_INPROGRESS.labels(type="sync", executor=self._name).dec()

    def submit(self, fn, *args, **kwargs):  # pylint: disable=arguments-differ
        """Immediately invokes `fn(*args, **kwargs)` and returns a future
        with the result (or exception)."""
        with self._shutdown.ensure_alive():
            future = Future()
            track_future(future, type="sync", executor=self._name)

            try:
                result = fn(*args, **kwargs)
                future.set_result(result)
            except Exception:
                copy_exception(future)

            return future
