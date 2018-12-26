from more_executors._wrapped import \
    CustomizableThreadPoolExecutor, \
    CustomizableProcessPoolExecutor
from more_executors._bind import BoundCallable
from more_executors.map import MapExecutor
from more_executors.flat_map import FlatMapExecutor
from more_executors.retry import RetryExecutor
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
        'with_flat_map',
        'with_poll',
        'with_timeout',
        'with_throttle',
        'with_cancel_on_shutdown',
        'with_asyncio',
        'bind',
    ]

    @classmethod
    def bind(cls, executor, fn):
        """Bind a callable to an executor.

        - `executor` - an `Executor` instance
        - `fn` - any function or callable

        Returns a new callable which, when invoked, will submit `fn` to `executor` and return
        the resulting future.

        The returned callable provides the `Executors.with_*` methods, which may be chained to
        further customize the behavior of the callable.

        ### **Example**

        Consider this code to fetch data from a list of URLs expected to provide JSON,
        with up to 8 concurrent requests and retries on failure, without using `bind`:

            executor = Executors.thread_pool(max_workers=8). \\
                with_map(lambda response: response.json()). \\
                with_retry()

            futures = [executor.submit(requests.get, url)
                       for url in urls]

        The following code using `bind` is functionally equivalent:

            async_get = Executors.thread_pool(max_workers=8). \\
                bind(requests.get). \\
                with_map(lambda response: response.json()). \\
                with_retry()

            futures = [async_get(url) for url in urls]

        The latter example using `bind` is more readable because the order of the calls to set
        up the pipeline more closely reflects the order in which the pipeline executes at
        runtime.

        In contrast, without using `bind`, the *first* step of the pipeline - `requests.get` -
        appears at the *end* of the code, which is harder to follow.

        *Since version 1.13.0*
        """
        return BoundCallable(executor, fn)

    @classmethod
    def thread_pool(cls, *args, **kwargs):
        """Creates a new `concurrent.futures.ThreadPoolExecutor` with the given arguments."""
        return CustomizableThreadPoolExecutor(*args, **kwargs)

    @classmethod
    def process_pool(cls, *args, **kwargs):
        """Creates a new `concurrent.futures.ProcessPoolExecutor` with the given arguments."""
        return CustomizableProcessPoolExecutor(*args, **kwargs)

    @classmethod
    def sync(cls, *args, **kwargs):
        """Creates a new `more_executors.sync.SyncExecutor`.

        Submitted functions will be immediately invoked on the calling thread."""
        return SyncExecutor(*args, **kwargs)

    @classmethod
    def _customize(cls, delegate, executor_class, *args, **kwargs):
        if isinstance(delegate, BoundCallable):
            executor = delegate._BoundCallable__executor
            bound_fn = delegate._BoundCallable__fn
            new_executor = executor_class(executor, *args, **kwargs)
            return cls.bind(new_executor, bound_fn)

        return executor_class(delegate, *args, **kwargs)

    @classmethod
    def with_retry(cls, executor, *args, **kwargs):
        """Wrap an executor in a `more_executors.retry.RetryExecutor`.

        Submitted functions will be retried on failure.
        """
        return cls._customize(executor, RetryExecutor, *args, **kwargs)

    @classmethod
    def with_map(cls, executor, *args, **kwargs):
        """Wrap an executor in a `more_executors.map.MapExecutor`.

        Submitted callables will have their output transformed by the given function.
        """
        return cls._customize(executor, MapExecutor, *args, **kwargs)

    @classmethod
    def with_flat_map(cls, executor, *args, **kwargs):
        """Wrap an executor in a `more_executors.flat_map.FlatMapExecutor`.

        Submitted callables will have their output transformed by the given
        `Future`-producing function.

        *Since version 1.12.0*
        """
        return cls._customize(executor, FlatMapExecutor, *args, **kwargs)

    @classmethod
    def with_poll(cls, executor, *args, **kwargs):
        """Wrap an executor in a `more_executors.poll.PollExecutor`.

        Submitted callables will have their output passed into the poll function.
        See the class documentation for more information.
        """
        return cls._customize(executor, PollExecutor, *args, **kwargs)

    @classmethod
    def with_timeout(cls, executor, *args, **kwargs):
        """Wrap an executor in a `more_executors.timeout.TimeoutExecutor`.

        Returned futures will be cancelled if they've not completed within the
        given timeout.

        *Since version 1.7.0*
        """
        return cls._customize(executor, TimeoutExecutor, *args, **kwargs)

    @classmethod
    def with_throttle(cls, executor, *args, **kwargs):
        """Wrap an executor in a `more_executors.throttle.ThrottleExecutor`.

        *Since version 1.9.0*
        """
        return cls._customize(executor, ThrottleExecutor, *args, **kwargs)

    @classmethod
    def with_cancel_on_shutdown(cls, executor, *args, **kwargs):
        """Wrap an executor in a `more_executors.cancel_on_shutdown.CancelOnShutdownExecutor`.

        Returned futures will have `cancel` invoked if the executor is shut down
        before the future has completed."""
        return cls._customize(executor, CancelOnShutdownExecutor, *args, **kwargs)

    @classmethod
    def with_asyncio(cls, executor, *args, **kwargs):
        """Wrap an executor in a `more_executors.asyncio.AsyncioExecutor`.

        Returned futures will be
        [`asyncio` futures](https://docs.python.org/3/library/asyncio-task.html)
        rather than `concurrent.futures` futures, i.e. may be used with the `await`
        keyword and coroutines.

        Note that since the other executors from the `Executors` class are designed
        for use with `concurrent.futures`, if an executor is being configured using
        chained `with_*` methods, this must be the last method called.

        Only usable for Python >= 3.5.

        *Since version 1.7.0*
        """
        return cls._customize(executor, AsyncioExecutor, *args, **kwargs)
