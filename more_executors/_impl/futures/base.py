# -*- coding: utf-8 -*-

from concurrent.futures import Future

from ..executors import Executors
from ..common import copy_exception


def f_return(x):
    """Return a future which provides the value `x`.

    Signature: :code:`A ⟶ Future<A>`

    Arguments:
        x
            A value to be returned

    Returns:
        :class:`~concurrent.futures.Future` of :obj:`x`
            A future immediately resolved with the value :obj:`x`.

    .. versionadded:: 1.19.0
    """
    return Executors.sync().submit(lambda: x)


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
    f.cancel()
    f.set_running_or_notify_cancel()
    return f


def chain_cancel(f_outer, f_inner):
    # attempt to cancel f_inner when f_outer is cancelled
    f_outer.add_done_callback(lambda f: f_inner.cancel() if f.cancelled() else False)


def wrap(f):
    return Executors.sync().flat_bind(lambda: f)
