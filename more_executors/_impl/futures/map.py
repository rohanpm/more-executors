# -*- coding: utf-8 -*-

from .base import wrap
from .check import ensure_future


@ensure_future
def f_map(future, fn=None, error_fn=None):
    """Map the output value of a future using the given functions.

    Signature: :code:`Future<A>, fn<A⟶B> ⟶ Future<B>`

    Arguments:
        future (~concurrent.futures.Future)
            Any future.
        fn (callable)
            Any callable to be applied on successful futures.
            This function is provided the result of the input future.
        error_fn (callable)
            Any callable to be applied on unsuccessful futures.
            This function is provided the exception of the input future.

    Returns:
        :class:`~concurrent.futures.Future`
            A future resolved with:

            - the returned value of :code:`fn(future.result())`
            - or the returned value of :code:`error_fn(future.exception())`
            - or with the exception raised by :obj:`future`, :obj:`fn` or :obj:`error_fn`.

    .. versionadded:: 1.19.0

    .. versionchanged:: 2.2.0
       Introduced ``error_fn``.
    """
    return wrap(future).with_map(fn=fn, error_fn=error_fn)()


@ensure_future
def f_flat_map(future, fn=None, error_fn=None):
    """Map the output value of a future using the given future-returning functions.

    Like :meth:`f_map`, except that the mapping functions must return a future,
    and that future will be flattened into the output value (avoiding a nested future).

    Signature: :code:`Future<A>, fn<A⟶Future<B>> ⟶ Future<B>`

    Arguments:
        future (~concurrent.futures.Future)
            Any future.
        fn (callable)
            Any future-returning callable to be applied on successful futures.
            This function is provided the result of the input future.
        error_fn (callable)
            Any future-returning callable to be applied on unsuccessful futures.
            This function is provided the exception of the input future.

    Returns:
        :class:`~concurrent.futures.Future`
            A future which is:

            - equivalent to that returned by :obj:`fn` if input future succeeded
            - or equivalent to that returned by :obj:`error_fn` if input future failed
            - or resolved with an exception if any of :obj:`future`, :obj:`fn` or
              :obj:`error_fn` failed

    .. versionadded:: 1.19.0

    .. versionchanged:: 2.2.0
       Introduced ``error_fn``.
    """
    return wrap(future).with_flat_map(fn=fn, error_fn=error_fn)()
