# -*- coding: utf-8 -*-

from concurrent.futures import Future

from ..executors import Executors
from ..common import copy_exception
from ..metrics import track_future

EXECUTOR = Executors.sync(name="internal")


def f_return(x=None):
    """Return a future which provides the value `x`.

    Signature: :code:`A ⟶ Future<A>`

    Arguments:
        x
            A value to be returned

    Returns:
        :class:`~concurrent.futures.Future` of :obj:`x`
            A future immediately resolved with the value :obj:`x`.

    .. versionadded:: 1.19.0
    .. versionchanged:: 2.1.0
        value now defaults to :code:`None`
    """
    future = Future()
    track_future(future, type="return", executor="none")
    future.set_result(x)
    return future


def f_return_error(x, traceback=None):
    """Return a future which returns/raises the exception `x`.

    Arguments:

        x (Exception)
            An exception to be returned/raised.

        traceback (traceback)
            An optional traceback associated with the exception.

            This argument should only be provided on Python 2.x.
            It will be used in the value returned from
            :meth:`concurrent.futures.Future.exception_info`,
            which only exists on Python 2.

    Returns:
        :class:`~concurrent.futures.Future` of :obj:`x`
            A future immediately resolved with the exception :obj:`x`.

    .. versionadded:: 1.19.0
    """

    f = Future()
    track_future(f, type="return_error", executor="none")
    copy_exception(f, x, traceback)
    return f


def f_return_cancelled():
    """
    Returns:
        :class:`~concurrent.futures.Future`
            A future which is cancelled.

    .. versionadded:: 1.19.0
    """
    f = Future()
    track_future(f, type="return_cancelled", executor="none")
    f.cancel()
    f.set_running_or_notify_cancel()
    return f


class WeakCallback(object):
    # A wrapper for a single-call callback which breaks the reference
    # to the callback at time of call.
    #
    # The point is to avoid futures holding references to each other
    # unnecessarily.  Our own future base class already throws away
    # callbacks as they're called, but the standard concurrent.futures.Future
    # does not.
    def __init__(self, delegate):
        self.__delegate = delegate

    def __call__(self, *args, **kwargs):
        delegate = self.__delegate
        del self.__delegate
        return delegate(*args, **kwargs)


weak_callback = WeakCallback


def chain_cancel(f_outer, f_inner):
    # attempt to cancel f_inner when f_outer is cancelled
    f_outer.add_done_callback(
        weak_callback(lambda f: f_inner.cancel() if f.cancelled() else False)
    )


def wrap(f):
    return EXECUTOR.flat_bind(lambda: f)
