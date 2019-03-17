from .wrapped import \
    CustomizableThreadPoolExecutor, \
    CustomizableProcessPoolExecutor
from .bind import BoundCallable
from .map import MapExecutor
from .flat_map import FlatMapExecutor
from .retry import RetryExecutor
from .poll import PollExecutor
from .timeout import TimeoutExecutor
from .throttle import ThrottleExecutor
from .cancel_on_shutdown import CancelOnShutdownExecutor
from .sync import SyncExecutor
from .asyncio import AsyncioExecutor


class Executors(object):
    """Convenience methods for creating executors.

    This class produces wrapped executors which may be customized
    by use of the `with_*` methods, as in the following example:

    >>> Executors.thread_pool(max_workers=4).with_retry().with_map(lambda x: x*2)

    Produces a thread pool executor which will retry on failure
    and multiply all output values by 2."""

    @classmethod
    def bind(cls, executor, fn):
        """Bind a synchronous callable to an executor.

        If the callable returns a future, consider using :meth:`flat_bind` instead.

        Arguments:
            executor (~concurrent.futures.Executor): an executor
            fn (callable): any function or callable

        Returns:
            callable:
                A new callable which, when invoked, will submit `fn` to `executor` and return
                the resulting future.

                This returned callable provides the `Executors.with_*` methods, which may be
                chained to further customize the behavior of the callable.

        .. versionadded:: 1.13.0
        """
        return BoundCallable(executor, fn)

    @classmethod
    def flat_bind(cls, executor, fn):
        """Bind an asynchronous callable to an executor.

        This convenience method should be used in preference to :meth:`bind`
        when the bound callable returns a future, in order to avoid a nested
        future in the returned value. It is equivalent to:

        >>> bind(fn).with_flat_map(lambda future: future)

        Arguments:
            executor (~concurrent.futures.Executor): an executor
            fn (callable): any function or callable which returns a future

        Returns:
            callable:
                A new callable which, when invoked, will submit `fn` to `executor` and return
                the resulting (flattened) future.

                This returned callable provides the `Executors.with_*` methods, which may be
                chained to further customize the behavior of the callable.

        .. versionadded:: 1.16.0
        """
        return cls.bind(executor, fn).with_flat_map(lambda f: f)

    @classmethod
    def thread_pool(cls, *args, **kwargs):
        """Create a thread pool executor.

        Returns:
            ~concurrent.futures.ThreadPoolExecutor:
                a new executor, initialized with the given arguments
        """
        return CustomizableThreadPoolExecutor(*args, **kwargs)

    @classmethod
    def process_pool(cls, *args, **kwargs):
        """Create a process pool executor.

        Returns:
            ~concurrent.futures.ProcessPoolExecutor:
                a new executor, initialized with the given arguments
        """
        return CustomizableProcessPoolExecutor(*args, **kwargs)

    @classmethod
    def sync(cls, *args, **kwargs):
        """Creates a new synchronous executor.

        Returns:
            ~more_executors.sync.SyncExecutor:
                a new synchronous executor

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
        """
        Returns:
            ~more_executors.retry.RetryExecutor:
                a new executor which will retry callables on failure
        """
        return cls._customize(executor, RetryExecutor, *args, **kwargs)

    @classmethod
    def with_map(cls, executor, *args, **kwargs):
        """
        Returns:
            ~more_executors.map.MapExecutor:
                a new executor which will transform results through the given function
        """
        return cls._customize(executor, MapExecutor, *args, **kwargs)

    @classmethod
    def with_flat_map(cls, executor, *args, **kwargs):
        """
        Returns:
            ~more_executors.flat_map.FlatMapExecutor:
                a new executor which will transform results through the given
                :class:`~concurrent.futures.Future`-providing function

        .. versionadded:: 1.12.0
        """
        return cls._customize(executor, FlatMapExecutor, *args, **kwargs)

    @classmethod
    def with_poll(cls, executor, *args, **kwargs):
        """
        Returns:
            ~more_executors.poll.PollExecutor:
                a new executor which produces polled futures.

                Submitted callables will have their output passed into
                a poll function.
        """
        return cls._customize(executor, PollExecutor, *args, **kwargs)

    @classmethod
    def with_timeout(cls, executor, *args, **kwargs):
        """
        Returns:
            ~more_executors.timeout.TimeoutExecutor:
                a new executor which will attempt to cancel any futures if they've
                not completed within the given timeout.

        .. versionadded:: 1.7.0
        """
        return cls._customize(executor, TimeoutExecutor, *args, **kwargs)

    @classmethod
    def with_throttle(cls, executor, *args, **kwargs):
        """
        Returns:
            ~more_executors.throttle.ThrottleExecutor:
                a new executor which enforces a limit on the number of concurrently
                pending futures.

        .. versionadded:: 1.9.0
        """
        return cls._customize(executor, ThrottleExecutor, *args, **kwargs)

    @classmethod
    def with_cancel_on_shutdown(cls, executor, *args, **kwargs):
        """
        Returns:
            ~more_executors.cancel_on_shutdown.CancelOnShutdownExecutor:
                a new executor which attempts to cancel any pending futures when
                the executor is shut down.
        """
        return cls._customize(executor, CancelOnShutdownExecutor, *args, **kwargs)

    @classmethod
    def with_asyncio(cls, executor, *args, **kwargs):
        """
        Returns:
            ~more_executors.asyncio.AsyncioExecutor:
                a new executor which returns :class:`asyncio.Future` instances
                rather than :class:`concurrent.futures.Future` instances, i.e. may be used
                with the `await` keyword and coroutines.

        .. note::
            Since the other executors from :class:`Executors` class are designed
            for use with :class:`concurrent.futures.Future`, if an executor is being
            configured using chained `with_*` methods, this must be the last method called.

        .. note::
            Only usable for Python >= 3.5.

        .. versionadded:: 1.7.0
        """
        return cls._customize(executor, AsyncioExecutor, *args, **kwargs)
