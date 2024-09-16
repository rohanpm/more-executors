# -*- coding: utf-8 -*-

from threading import Lock
import logging
from concurrent.futures import Future

from .base import chain_cancel, weak_callback
from ..common import copy_future_exception, try_set_result
from .check import ensure_futures
from ..logwrap import LogWrapper
from ..metrics import track_future

LOG = LogWrapper(logging.getLogger("more_executors.futures"))


# Our futures here know whether they are an AND or OR future and
# keep a reference back to the underlying boolean oper.
# This allows us to be more efficient in certain scenarios.
class BoolFuture(Future):
    def __init__(self, oper):
        self.oper = oper
        super(BoolFuture, self).__init__()


class AndFuture(BoolFuture):
    pass


class OrFuture(BoolFuture):
    pass


class BoolOperation(object):
    FUTURE_CLASS = BoolFuture

    def __init__(self, fs):
        future_types = {}
        remainder = []

        self.fs = {}
        for f in fs:
            self.fs[f] = True
            if isinstance(f, BoolFuture):
                future_types.setdefault(type(f), []).append(f.oper)
            else:
                remainder.append(f)

        if list(future_types.keys()) == [self.FUTURE_CLASS]:
            # Special case: we are being called with input futures
            # which are themselves the output of f_and/f_or, and all
            # of the same type as our current operation, for example:
            # f = f_and(...)
            # f = f_and(f, ...)
            # f = f_and(f, ...)
            # f = f_and(f, ...)
            # ...and so on.
            #
            # In that case: rather than keeping the input futures as
            # we normally do, we can look inside of them and pull out
            # their constituent futures. This allows us to return a more
            # flat data structure, reducing the number of chained futures.
            # It's useful to do this because a large number of chained
            # futures can lead to a stack overflow as completion callbacks
            # are invoked.
            self.fs = {}
            for oper in future_types[self.FUTURE_CLASS]:
                with oper.lock:
                    if oper.done:
                        # FIXME: seems like we're still introducing a (hopefully
                        # very small) chance of stack overflow here.
                        # We could be in the small window of time where oper.done
                        # is true but oper.out.set_result hasn't been called.
                        # If so, then we're unflattening the structure again.
                        # In theory it could happen for enough futures to cause
                        # an overflow. Is there a practical way to rule it out
                        # entirely?
                        self.fs[oper.out] = True
                    else:
                        self.fs.update(oper.fs)
            for f in remainder:
                self.fs[f] = True
            fs = list(self.fs.keys())

        self.done = False
        self.lock = Lock()
        self.out = self.FUTURE_CLASS(self)

        for f in fs:
            chain_cancel(self.out, f)
            f.add_done_callback(weak_callback(self.handle_done))

    def get_state_update(self, f):
        raise NotImplementedError()  # pragma: no cover

    def handle_done(self, f):
        set_result = False
        set_exception = False
        cancel_futures = set()

        with self.lock:
            if self.done:
                return

            del self.fs[f]

            (set_result, set_exception, cancel_futures) = self.get_state_update(f)

        if set_result:
            try_set_result(self.out, f.result())
        if set_exception:
            copy_future_exception(f, self.out)

        for to_cancel in cancel_futures:
            to_cancel.cancel()


class OrOperation(BoolOperation):
    FUTURE_CLASS = OrFuture

    def get_state_update(self, f):
        set_result = False
        set_exception = False
        cancel_futures = set()

        # If it's the last result or it's a successful result:
        if (not self.fs) or (not f.cancelled() and not f.exception() and f.result()):
            self.done = True
            cancel_futures = list(self.fs.keys())
            if f.cancelled():
                # Cancelled => output is cancelled
                cancel_futures.append(self.out)
            elif f.exception():
                # Failed
                set_exception = True
            else:
                # Last or successful
                set_result = True

        return (set_result, set_exception, cancel_futures)


@ensure_futures
def f_or(f, *fs):
    """Boolean ``OR`` over a number of futures.

    Signature: :code:`Future<A>[, Future<B>[, ...]] ⟶ Future<A|B|...>`

    Arguments:
        f (~concurrent.futures.Future)
            Any future
        fs (~concurrent.futures.Future)
            Any futures

    Returns:
        :class:`~concurrent.futures.Future`
            A future resolved from the inputs using ``OR`` semantics:

            - Resolved with the earliest true value returned by an input
              future, if any.
            - Otherwise, resolved with the latest false value or exception
              returned by the input futures.

    .. note::
        This function is tested with up to 100,000 input futures.
        Exceeding this limit may result in performance issues.

    .. versionadded:: 1.19.0
    """
    if not fs:
        return f

    oper = OrOperation([f] + list(fs))
    track_future(oper.out, type="or")
    return oper.out


class AndOperation(BoolOperation):
    FUTURE_CLASS = AndFuture

    def get_state_update(self, f):
        set_result = False
        set_exception = False
        cancel_futures = set()

        if f.cancelled():
            # Cancelled => output is cancelled
            self.done = True
            cancel_futures = list(self.fs.keys())
            cancel_futures.append(self.out)
        elif f.exception():
            # Failed => we're done
            self.done = True
            set_exception = True
            cancel_futures = list(self.fs.keys())
        elif (not f.result()) or (not self.fs):
            # Falsey result or last result => we're done
            self.done = True
            cancel_futures = list(self.fs.keys())
            set_result = True

        return (set_result, set_exception, cancel_futures)


@ensure_futures
def f_and(f, *fs):
    """Boolean ``AND`` over a number of futures.

    Signature: :code:`Future<A>[, Future<B>[, ...]] ⟶ Future<A|B|...>`

    Arguments:
        f (~concurrent.futures.Future)
            Any future
        fs (~concurrent.futures.Future)
            Any futures

    Returns:
        :class:`~concurrent.futures.Future`
            A future resolved from the inputs using ``AND`` semantics:

            - Resolved with the latest value returned by an input
              future, if all futures are resolved with true values.
            - Otherwise, resolved with the earliest false value or exception
              returned by the input futures.

    .. note::
        This function is tested with up to 100,000 input futures.
        Exceeding this limit may result in performance issues.

    .. versionadded:: 1.19.0
    """
    if not fs:
        return f

    oper = AndOperation([f] + list(fs))
    track_future(oper.out, type="and")
    return oper.out
