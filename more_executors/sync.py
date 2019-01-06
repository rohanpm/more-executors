from concurrent.futures import Executor, Future

from more_executors._common import _copy_exception
from more_executors._wrap import CanCustomizeBind


class SyncExecutor(CanCustomizeBind, Executor):
    """An executor which immediately invokes all submitted callables."""

    def __init__(self, logger=None):
        """
        Parameters:
            logger (~logging.Logger):
                a logger used for messages from this executor
        """
        super(SyncExecutor, self).__init__()

    def submit(self, fn, *args, **kwargs):
        """Immediately invokes `fn(*args, **kwargs)` and returns a future
        with the result (or exception)."""
        future = Future()
        try:
            result = fn(*args, **kwargs)
            future.set_result(result)
        except Exception:
            _copy_exception(future)
        return future
