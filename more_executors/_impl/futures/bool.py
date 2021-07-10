# -*- coding: utf-8 -*-

from threading import Lock
import logging
from concurrent.futures import Future

from .base import chain_cancel, weak_callback
from ..common import copy_future_exception
from .check import ensure_futures
from ..logwrap import LogWrapper
from ..metrics import track_future

LOG = LogWrapper(logging.getLogger("more_executors.futures"))


class BoolOperation(object):
    def __init__(self, fs):
        self.fs = {}
        for f in fs:
            self.fs[f] = True

        self.done = False
        self.lock = Lock()
        self.out = Future()

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
            self.out.set_result(f.result())
        if set_exception:
            copy_future_exception(f, self.out)

        for to_cancel in cancel_futures:
            to_cancel.cancel()


class OrOperation(BoolOperation):
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
