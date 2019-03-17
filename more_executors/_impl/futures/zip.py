# -*- coding: utf-8 -*-

from .base import f_return, chain_cancel
from .map import f_map, f_flat_map


def f_zip(*fs):
    """Create a new future holding the return values of any number of input futures.

    Signature: :code:`Future<A>[, Future<B>[, ...]] ⟶ Future<A[, B[, ...]]>`

    Arguments:
        fs (~concurrent.futures.Future)
            Any number of futures.

    Returns:
        :class:`~concurrent.futures.Future` of :class:`tuple`
            A future holding the returned values of all input futures as a tuple.
            The returned tuple has the same length and order as the input futures.

            Alternatively, a future raising an exception, if any input futures raised
            an exception.

    .. versionadded:: 1.19.0
    """
    if not fs:
        return f_return(())

    f = fs[0]
    rest = f_zip(*fs[1:])

    def prepender(f_result):
        return f_map(rest, lambda result: tuple([f_result] + list(result)))

    out = f_flat_map(f, prepender)
    chain_cancel(out, f)
    chain_cancel(out, rest)
    return out
