from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial

from more_executors.map import MapExecutor
from more_executors.retry import RetryExecutor, ExceptionRetryPolicy
from more_executors.poll import PollExecutor


class Executors(object):
    """Convenience methods for creating executors.

    This class produces wrapped executors which may be customized
    by use of the `with_*` methods, as in the following example:

    ```
    Executors.thread_pool(max_workers=4).with_retry().with_map(lambda x: x*2)
    ```

    Produces a thread pool executor which will retry on failure
    and multiply all output values by 2."""

    _WRAP_METHODS = [
        'with_retry',
        'with_map',
        'with_poll',
    ]

    @classmethod
    def wrap(cls, executor):
        """Wrap an executor for configuration.

        This adds all `with_*` methods from this class onto the executor.
        When invoked, the executor is implicitly passed as the first argument to the method."""
        for name in cls._WRAP_METHODS:
            unbound_fn = getattr(cls, name)
            bound_fn = partial(unbound_fn, executor)
            setattr(executor, name, bound_fn)
        return executor

    @classmethod
    def thread_pool(cls, *args, **kwargs):
        """Creates a new `concurrent.futures.ThreadPoolExecutor` with the given arguments."""
        return cls.wrap(ThreadPoolExecutor(*args, **kwargs))

    @classmethod
    def process_pool(cls, *args, **kwargs):
        """Creates a new `concurrent.futures.ProcessPoolExecutor` with the given arguments."""
        return cls.wrap(ProcessPoolExecutor(*args, **kwargs))

    @classmethod
    def with_retry(cls, executor, retry_policy=None):
        """Wrap an executor in a `more_executors.retry.RetryExecutor`.

        Submitted functions will be retried on failure.

        - `retry_policy`: the `more_executors.retry.RetryPolicy` to be used; if omitted,
                          a reasonable default is applied which will retry for several minutes."""
        if not retry_policy:
            retry_policy = ExceptionRetryPolicy.new_default()
        return cls.wrap(RetryExecutor(executor, retry_policy))

    @classmethod
    def with_map(cls, executor, fn):
        """Wrap an executor in a `more_executors.map.MapExecutor`.

        Submitted callables will have their output transformed by the given function.

        - `fn`: a function used to transform each output value from the executor"""
        return cls.wrap(MapExecutor(executor, fn))

    @classmethod
    def with_poll(cls, executor, fn, cancel_fn=None, default_interval=5.0):
        """Wrap an executor in a `more_executors.poll.PollExecutor`.

        Submitted callables will have their output passed into the poll function.
        See the class documentation for more information on the poll and cancel
        functions.

        - `fn`: a function used for polling results.
        - `cancel_fn`: a function called when a future is cancelled.
        - `default_interval`: default interval between polls, in seconds."""
        return cls.wrap(PollExecutor(executor, fn, cancel_fn, default_interval))
