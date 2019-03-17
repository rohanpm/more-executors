# -*- coding: utf-8 -*-

from .base import wrap, f_return
from .apply import f_apply


def f_map(future, fn):
    """Map the output value of a future using the given function.

    Signature: :code:`Future<A>, fn<A⟶B> ⟶ Future<B>`

    Arguments:
        future (~concurrent.futures.Future)
            Any future.
        fn (callable)
            Any callable.

    Returns:
        :class:`~concurrent.futures.Future`
            A future resolved with the returned value of :code:`fn(future.result())`,
            or with the exception raised by :obj:`future` or :obj:`fn`.

    .. versionadded:: 1.19.0
    """
    future_fn = f_return(fn)
    return f_apply(future_fn, future)


def f_flat_map(future, fn):
    """Map the output value of a future using the given future-returning function.

    Like :meth:`f_map`, except that the mapping function must return a future,
    and that future will be flattened into the output value (avoiding a nested future).

    Signature: :code:`Future<A>, fn<A⟶Future<B>> ⟶ Future<B>`

    Arguments:
        future (~concurrent.futures.Future)
            Any future.
        fn (callable)
            Any callable which returns a future.

    Returns:
        :class:`~concurrent.futures.Future`
            A future equivalent to that returned by :obj:`fn`, or resolved with an exception
            if :obj:`future` or :obj:`fn` failed.

    .. versionadded:: 1.19.0
    """
    return wrap(future).with_flat_map(fn)()
