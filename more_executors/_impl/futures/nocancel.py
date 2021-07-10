# -*- coding: utf-8 -*-

from ..map import MapFuture
from .check import ensure_future
from ..metrics import track_future


class NoCancelFuture(MapFuture):
    def cancel(self):
        return False


@ensure_future
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
    return track_future(NoCancelFuture(future, lambda x: x), type="nocancel")
