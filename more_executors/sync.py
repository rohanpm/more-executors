"""An executor which invokes callables synchronously."""
from concurrent.futures import Executor, Future


__pdoc__ = {}
__pdoc__['SyncExecutor.map'] = None
__pdoc__['SyncExecutor.shutdown'] = None


class SyncExecutor(Executor):
    """An `Executor` which immediately invokes all submitted callables.

    This executor is useful for testing.  With executor implementations
    such as `ThreadPoolExecutor`, it's possible (though rare) for a future
    to be resolved before being returned to the caller.  This may have an
    impact on the caller's code (for example, `future.add_done_callback`
    if called on a done future will invoke callbacks immediately in the calling
    thread).

    With this executor, that's guaranteed to always be the case.  Thus it can
    be used to test code paths which are otherwise rarely triggered.
    """
    def submit(self, fn, *args, **kwargs):
        """Immediately invokes `fn(*args, **kwargs)` and returns a future
        with the result."""
        future = Future()
        try:
            result = fn(*args, **kwargs)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)
        return future
