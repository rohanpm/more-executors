from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial

from more_executors.map import MapExecutor
from more_executors.retry import RetryExecutor, ExceptionRetryPolicy
from more_executors.poll import PollExecutor
from more_executors.timeout import TimeoutExecutor
from more_executors.throttle import ThrottleExecutor
from more_executors.cancel_on_shutdown import CancelOnShutdownExecutor
from more_executors.sync import SyncExecutor
from more_executors.asyncio import AsyncioExecutor


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
        'with_timeout',
        'with_throttle',
        'with_cancel_on_shutdown',
        'with_asyncio',
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
    def sync(cls, *args, **kwargs):
        """Creates a new `more_executors.sync.SyncExecutor`.

        Submitted functions will be immediately invoked on the calling thread."""
        return cls.wrap(SyncExecutor(*args, **kwargs))

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

    @classmethod
    def with_timeout(cls, executor, timeout):
        """Wrap an executor in a `more_executors.timeout.TimeoutExecutor`.

        Returned futures will be cancelled if they've not completed within the
        given timeout.

        - `timeout`: timeout value, in seconds (float)

        *Since version 1.7.0*
        """
        return cls.wrap(TimeoutExecutor(executor, timeout))

    @classmethod
    def with_throttle(cls, executor, count):
        """Wrap an executor in a `more_executors.throttle.ThrottleExecutor`.

        - `count`: the returned executor will ensure that no more than this
                   many futures are running concurrently

        *Since version 1.9.0*
        """
        return cls.wrap(ThrottleExecutor(executor, count))

    @classmethod
    def with_cancel_on_shutdown(cls, executor):
        """Wrap an executor in a `more_executors.cancel_on_shutdown.CancelOnShutdownExecutor`.

        Returned futures will have `cancel` invoked if the executor is shut down
        before the future has completed."""
        return cls.wrap(CancelOnShutdownExecutor(executor))

    @classmethod
    def with_asyncio(cls, executor, loop=None):
        """Wrap an executor in a `more_executors.asyncio.AsyncioExecutor`.

        Returned futures will be
        [`asyncio` futures](https://docs.python.org/3/library/asyncio-task.html)
        rather than `concurrent.futures` futures, i.e. may be used with the `await`
        keyword and coroutines.

        - `executor`: a delegate executor, which must produce `concurrent.futures`
          future objects
        - `loop`: default `asyncio` event loop for use with the returned `asyncio`
          futures

        Note that since the other executors from the `Executors` class are designed
        for use with `concurrent.futures`, if an executor is being configured using
        chained `with_*` methods, this must be the last method called.

        Only usable for Python >= 3.5.

        *Since version 1.7.0*
        """
        return AsyncioExecutor(executor, loop)
