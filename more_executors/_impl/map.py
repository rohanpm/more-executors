from concurrent.futures import Executor

from .common import _Future, copy_exception, copy_future_exception
from .wrap import CanCustomizeBind
from .metrics import metrics, track_future
from .helpers import ShutdownHelper


def identity(x):
    return x


class MapFuture(_Future):
    def __init__(self, delegate, map_fn=None, error_fn=None):
        super(MapFuture, self).__init__()
        self._map_fn = map_fn or identity
        self._error_fn = error_fn
        self._set_delegate(delegate)

    def _set_delegate(self, delegate):
        with self._me_lock:
            self._delegate = delegate

        if delegate:
            self._delegate.add_done_callback(self._delegate_resolved)

    def _delegate_failed(self, delegate):
        if self._error_fn is None:
            copy_future_exception(delegate, self)
            return

        ex = delegate.exception()

        try:
            return self._error_fn(ex)
        except Exception as inner_ex:
            if ex is inner_ex:
                # fn raised exactly the same thing:
                # then copy directly from the future
                copy_future_exception(delegate, self)
            else:
                # fn raised something else:
                # then copy that
                copy_exception(self)

    def _delegate_resolved(self, delegate):
        assert delegate is self._delegate, "BUG: called with %s, expected %s" % (
            delegate,
            self._delegate,
        )

        if delegate.cancelled():
            return

        ex = delegate.exception()
        if ex is not None:
            result = self._delegate_failed(delegate)
            if self.done():
                return
        else:
            result = delegate.result()
            try:
                result = self._map_fn(result)
            except Exception:
                copy_exception(self)
                return

        try:
            self._on_mapped(result)
        except Exception:
            copy_exception(self)

    def _on_mapped(self, result):
        self.set_result(result)

    def set_result(self, result):
        with self._me_lock:
            super(MapFuture, self).set_result(result)
        self._me_invoke_callbacks()

    def set_exception(self, exception):
        with self._me_lock:
            super(MapFuture, self).set_exception(exception)
        self._me_invoke_callbacks()

    def set_exception_info(self, exception, traceback):
        # For python2 compat.
        # pylint: disable=no-member
        with self._me_lock:
            super(MapFuture, self).set_exception_info(exception, traceback)
        self._me_invoke_callbacks()

    def running(self):
        with self._me_lock:
            if self.done():
                return False
            return self._delegate and (
                self._delegate.running() or self._delegate.done()
            )

    def _me_cancel(self):
        return self._delegate.cancel()


class MapExecutor(CanCustomizeBind, Executor):
    """An executor which delegates to another executor while mapping
    output values/exceptions through given functions.
    """

    _FUTURE_CLASS = MapFuture
    _TYPE = "map"

    @property
    def _metric_exec_total(self):
        return metrics.EXEC_TOTAL.labels(type=self._TYPE, executor=self._name)

    @property
    def _metric_exec_inprogress(self):
        return metrics.EXEC_INPROGRESS.labels(type=self._TYPE, executor=self._name)

    def __init__(self, delegate, fn=None, logger=None, name="default", **kwargs):
        """
        Arguments:
            delegate (~concurrent.futures.Executor):
                an executor to which callables will be submitted
            fn (callable):
                a callable applied to transform returned values
                of successful futures.

                This callable will be invoked with a single argument:
                the ``result()`` returned from a successful future.

                If omitted, no transformation occurs on ``result()``.
            error_fn (callable):
                a callable applied to transform returned values
                of unsuccessful futures.

                This callable will be invoked with a single argument:
                the ``exception()`` returned from a failed future.

                If omitted, no transformation occurs on ``exception()``.
            logger (~logging.Logger):
                a logger used for messages from this executor
            name (str):
                a name for this executor

        .. versionchanged:: 2.2.0
            Introduced ``error_fn``.

        .. versionchanged:: 2.7.0
            Introduced ``name``.
        """
        self._delegate = delegate
        self._fn = fn
        self._name = name
        self._shutdown = ShutdownHelper()
        self._error_fn = kwargs.get("error_fn")
        self._metric_exec_total.inc()
        self._metric_exec_inprogress.inc()

    def shutdown(self, wait=True, **_kwargs):
        if self._shutdown():
            self._metric_exec_inprogress.dec()
            self._delegate.shutdown(wait, **_kwargs)

    def submit(self, *args, **kwargs):  # pylint: disable=arguments-differ
        with self._shutdown.ensure_alive():
            inner_f = self._delegate.submit(*args, **kwargs)
            return track_future(
                self._FUTURE_CLASS(inner_f, self._fn, self._error_fn),
                type=self._TYPE,
                executor=self._name,
            )
