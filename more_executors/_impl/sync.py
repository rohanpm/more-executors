from concurrent.futures import Executor, Future

from .common import copy_exception
from .wrap import CanCustomizeBind


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
            copy_exception(future)
        return future
