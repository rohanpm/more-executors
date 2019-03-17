# -*- coding: utf-8 -*-

import weakref
from threading import Lock
import logging
from concurrent.futures import Future

from .base import chain_cancel
from ..common import copy_future_exception


LOG = logging.getLogger('more_executors.futures')


class BoolCallback(object):
    AWAITING_FIRST = 1
    AWAITING_SECOND = 2
    STOP = 3

    def __init__(self, output, f1, f2):
        self.state = self.AWAITING_FIRST
        self.output = output
        self.lock = Lock()
        self.f1 = weakref.ref(f1)
        self.f2 = weakref.ref(f2)

    def get_cancel_future(self, completed_future):
        f1 = self.f1()
        f2 = self.f2()

        if f1 and completed_future is f1 and f2:
            return f2
        if f2 and completed_future is f2 and f1:
            return f1

    def update_state(self, future, have_result):
        raise NotImplementedError()  # pragma: no cover

    def __call__(self, future):
        if self.output.cancelled():
            return

        exception = future.exception() if not future.cancelled() else None
        result = None
        set_result = None
        have_result = False
        set_exception = None
        cancel_future = None
        if not exception and not future.cancelled():
            result = future.result()
            have_result = True

        with self.lock:
            (set_result, set_exception, cancel_future) = self.update_state(future, have_result)

        if set_result:
            self.output.set_result(result)
        if set_exception:
            copy_future_exception(future, self.output)
        if cancel_future:
            cancelled = cancel_future.cancel()
            LOG.debug("cancel %s in callback for %s: %s", cancel_future, future, cancelled)


class OrCallback(BoolCallback):
    def update_state(self, future, have_result):
        set_result = None
        set_exception = None
        cancel_future = None

        if self.state == self.AWAITING_FIRST:
            if have_result and future.result():
                self.state = self.STOP
                set_result = True
                cancel_future = self.get_cancel_future(future)
                LOG.debug("f_or: set result on %s to %s from left=%s",
                          self.output, future.result(), future)
            else:
                self.state = self.AWAITING_SECOND
        elif self.state == self.AWAITING_SECOND:
            self.state = self.STOP
            if future.cancelled():
                cancel_future = self.output
            elif have_result:
                set_result = True
                LOG.debug("f_or: set result on %s to %s from right=%s",
                          self.output, future.result(), future)
            else:
                set_exception = True

        return (set_result, set_exception, cancel_future)


class AndCallback(BoolCallback):
    def update_state(self, future, have_result):
        set_result = None
        set_exception = None
        cancel_future = None

        if self.state == self.AWAITING_SECOND:
            self.state = self.STOP
            if future.cancelled():
                cancel_future = self.output
            elif future.exception():
                set_exception = True
            else:
                set_result = True
                LOG.info("f_and: set %s result %s due completion of %s",
                         self.output, future.result(), future)
        elif self.state == self.AWAITING_FIRST:
            if future.cancelled():
                cancel_future = self.output
                self.state = self.STOP
            elif future.exception():
                set_exception = True
                cancel_future = self.get_cancel_future(future)
                self.state = self.STOP
            elif not future.result():
                set_result = True
                cancel_future = self.get_cancel_future(future)
                self.state = self.STOP
            else:
                # This side gave a truthy result so await the other
                self.state = self.AWAITING_SECOND

        return (set_result, set_exception, cancel_future)


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

    .. versionadded:: 1.19.0
    """
    if not fs:
        return f

    f1 = f
    f2 = f_or(fs[0], *fs[1:])

    out = Future()
    chain_cancel(out, f1)
    chain_cancel(out, f2)
    callback = OrCallback(out, f1, f2)
    f1.add_done_callback(callback)
    f2.add_done_callback(callback)
    return out


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

    .. versionadded:: 1.19.0
    """
    if not fs:
        return f

    f1 = f
    f2 = f_and(fs[0], *fs[1:])

    out = Future()
    chain_cancel(out, f1)
    chain_cancel(out, f2)
    callback = AndCallback(out, f1, f2)
    f1.add_done_callback(callback)
    f2.add_done_callback(callback)
    return out
