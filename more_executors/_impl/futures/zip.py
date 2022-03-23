# -*- coding: utf-8 -*-
from concurrent.futures import Future
from threading import Lock
from functools import partial
from collections import namedtuple

from more_executors._impl.common import copy_future_exception
from .base import f_return, chain_cancel, weak_callback
from .check import ensure_futures
from ..metrics import track_future


# For small-ish tuples, we make f_zip return namedtuple instances
# which can be traced back to here rather than bare tuples. The point
# is to improve debuggability of code where the future returned by
# f_zip ends up being logged with repr(), as in that case only the
# result's type will be logged. Seeing e.g. 'ZipTuple3' in a crash log
# rather than 'tuple' could be potentially very helpful.
TUPLE_CLASSES = []
for i in range(0, 20):
    TUPLE_CLASSES.append(
        namedtuple("ZipTuple%s" % i, ["f%s" % idx for idx in range(0, i)])
    )


def maketuple(value):
    vlen = len(value)
    if vlen < len(TUPLE_CLASSES):
        return TUPLE_CLASSES[vlen](*value)
    return tuple(value)


class Zipper(object):
    def __init__(self, fs):
        self.fs = list(fs)
        self.out = Future()
        self.done = False
        self.lock = Lock()
        self.count_remaining = len(self.fs)

        for (idx, future) in enumerate(self.fs):
            chain_cancel(self.out, future)
            future.add_done_callback(weak_callback(partial(self.handle_done, idx)))

    def handle_done(self, index, f):
        set_result = False
        set_exception = False
        cancel = False

        with self.lock:
            if self.done:
                pass
            elif f.cancelled():
                self.done = True
                cancel = True
            elif f.exception():
                self.done = True
                set_exception = True
            else:
                self.fs[index] = f.result()
                self.count_remaining -= 1

                if self.count_remaining == 0:
                    self.done = True
                    set_result = True

        if cancel:
            self.out.cancel()
        if set_result:
            self.out.set_result(maketuple(self.fs))
        if set_exception:
            copy_future_exception(f, self.out)


@ensure_futures
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

            Alternatively, a future raising an exception or a cancelled future,
            if any input futures raised an exception or was cancelled.

    .. note::
        This function is tested with up to 100,000 input futures.
        Exceeding this limit may result in performance issues.

    .. versionadded:: 1.19.0
    """
    if not fs:
        return f_return(maketuple([]))

    return track_future(Zipper(fs).out, type="zip")
