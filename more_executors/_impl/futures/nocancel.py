# -*- coding: utf-8 -*-

from ..map import MapFuture


class NoCancelFuture(MapFuture):
    def cancel(self):
        return False


def f_nocancel(future):
    """Wrap a future to block cancellation.

    Signature: :code:`Future<X> ⟶ Future<X>`

    Arguments:
        future (~concurrent.futures.Future)
            Any future.

    Returns:
        :class:`~concurrent.futures.Future`
            A wrapped version of :obj:`future` which cannot be cancelled.

    .. versionadded:: 1.19.0
    """
    return NoCancelFuture(future, lambda x: x)
