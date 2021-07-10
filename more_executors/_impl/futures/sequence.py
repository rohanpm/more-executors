# -*- coding: utf-8 -*-

from concurrent.futures import Future

from .zip import f_zip
from .map import f_map

from ..common import copy_exception
from ..metrics import track_future


def f_sequence(futures):
    """Transform a list of futures into a future containing a list.

    Signature: :code:`list<Future<X>> ⟶ Future<list<X>>`

    Arguments:
        futures (iterable of :class:`~concurrent.futures.Future`)
            A list or other iterable of futures.

    Returns:
        :class:`~concurrent.futures.Future` of :class:`list`
            A future resolved with either:

            - a list holding the output value of each input future
            - or an exception, if any input future raised an exception

    .. note::
        This function is tested with up to 100,000 input futures.
        Exceeding this limit may result in performance issues.

    .. versionadded:: 1.19.0
    """
    return track_future(f_traverse(lambda x: x, futures), type="sequence")


def f_traverse(fn, xs):
    """Traverse over an iterable calling a future-returning function,
    and return a future holding the returned values as a list.

    Signature: :code:`fn<A⟶Future<B>>, iterable<A> ⟶ Future<list<B>>`

    Arguments:
        fn (callable)
            A unary function returning a future.
        xs (iterable)
            An iterable to be traversed.

    Returns:
        :class:`~concurrent.futures.Future` of :class:`list`
            A future resolved with either:

            - a list holding the resolved output values of :obj:`fn`
            - or an exception, if :obj:`fn` or any future produced by :obj:`fn` failed

    .. versionadded:: 1.19.0
    """
    try:
        futures = [fn(x) for x in xs]
    except Exception:
        future = Future()
        copy_exception(future)
        return future

    zipped = f_zip(*futures)
    return track_future(f_map(zipped, list), type="traverse")
