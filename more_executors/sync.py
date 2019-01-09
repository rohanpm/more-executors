from concurrent.futures import Executor, Future

from more_executors._common import _copy_exception
from more_executors._wrap import CanCustomizeBind


class SyncExecutor(CanCustomizeBind, Executor):
    """An executor which immediately invokes all submitted callables.

    This executor is useful for testing.  With executor implementations
    such as :class:`~concurrent.futures.ThreadPoolExecutor`, it's possible
    (though rare) for a future to be resolved before being returned to the
    caller.  This may have an impact on the caller's code (for example,
    :meth:`~concurrent.futures.Future.add_done_callback` if called on a done
    future will invoke callbacks immediately in the calling thread).

    With this executor, that's guaranteed to always be the case.  Thus it can
    be used to test code paths which are otherwise rarely triggered.
    """
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
