from concurrent.futures import Executor
from collections import namedtuple
from threading import RLock, Thread, Event
import weakref
import sys
import logging

from more_executors._common import _Future, _MAX_TIMEOUT
from more_executors._wrap import CanCustomizeBind


class _PollFuture(_Future):
    def __init__(self, delegate, executor):
        super(_PollFuture, self).__init__()
        self._delegate = delegate
        self._executor = executor
        self._delegate.add_done_callback(self._delegate_resolved)

    def _delegate_resolved(self, delegate):
        assert delegate is self._delegate, \
            "BUG: called with %s, expected %s" % (delegate, self._delegate)

        if delegate.cancelled():
            return
        elif delegate.exception():
            self.set_exception(delegate.exception())
        else:
            self._executor._register_poll(self, self._delegate)

    def _clear_delegate(self):
        with self._me_lock:
            self._delegate = None

    def set_result(self, result):
        with self._me_lock:
            if self.done():
                return
            super(_PollFuture, self).set_result(result)
        self._me_invoke_callbacks()

    def set_exception(self, exception):
        with self._me_lock:
            if self.done():
                return
            super(_PollFuture, self).set_exception(exception)
        self._me_invoke_callbacks()

    def running(self):
        with self._me_lock:
            if self._delegate:
                return self._delegate.running()
        # If delegate is removed, we're now polling or done.
        return False

    def _me_cancel(self):
        if self._delegate and not self._delegate.cancel():
            return False
        if not self._executor._run_cancel_fn(self):
            return False
        self._executor._deregister_poll(self)
        return True


PollDescriptor = namedtuple('PollDescriptor', ['result', 'yield_result', 'yield_exception'])

if sys.version_info[0] > 2:
    PollDescriptor.__doc__ = \
        """Represents an unresolved :class:`~concurrent.futures.Future`.

        The poll function used by :class:`PollExecutor` will be
        invoked with a list of PollDescriptor objects.
        """

    PollDescriptor.result.__doc__ = \
        """The result from the delegate executor's future, which should be used to
        drive the poll."""

    PollDescriptor.yield_result.__doc__ = \
        """The poll function can call this function to make the future yield the given result."""

    PollDescriptor.yield_exception.__doc__ = \
        """The poll function can call this function to make the future raise the given exception."""


class PollExecutor(CanCustomizeBind, Executor):
    """Instances of `PollExecutor` submit callables to a delegate executor
    and resolve the returned futures via a provided poll function.

    A cancel function may also be provided to perform additional processing
    when a returned future is cancelled.
    """

    def __init__(self, delegate, poll_fn, cancel_fn=None, default_interval=5.0, logger=None):
        """
        Parameters:

            delegate (~concurrent.futures.Executor):
                executor to which callables will be submitted

            poll_fn (callable):
                a `poll function`_ used to decide when futures should be resolved

            cancel_fn (callable):
                a `cancel function`_ invoked when future cancel is required

            default_interval (float):
                default interval between polls (in seconds)

            logger (~logging.Logger):
                a logger used for messages from this executor
        """
        self._log = logger if logger else logging.getLogger('PollExecutor')
        self._delegate = delegate
        self._default_interval = default_interval
        self._poll_fn = poll_fn
        self._cancel_fn = cancel_fn
        self._poll_descriptors = []
        self._poll_event = Event()

        poll_event = self._poll_event
        self_ref = weakref.ref(self, lambda _: poll_event.set())

        self._poll_thread = Thread(name='PollExecutor', target=_poll_loop, args=(self_ref,))
        self._poll_thread.daemon = True
        self._shutdown = False
        self._lock = RLock()

        self._poll_thread.start()

    def submit(self, fn, *args, **kwargs):
        delegate_future = self._delegate.submit(fn, *args, **kwargs)
        out = _PollFuture(delegate_future, self)
        out.add_done_callback(self._deregister_poll)
        return out

    def _register_poll(self, future, delegate_future):
        descriptor = PollDescriptor(
            delegate_future.result(),
            future.set_result,
            future.set_exception)
        with self._lock:
            self._poll_descriptors.append((future, descriptor))
            future._clear_delegate()
            self._poll_event.set()

    def _deregister_poll(self, future):
        with self._lock:
            self._poll_descriptors = [(f, d)
                                      for (f, d) in self._poll_descriptors
                                      if f is not future]

    def _run_cancel_fn(self, future):
        if not self._cancel_fn:
            # no cancel function => no veto of cancel
            return True

        descriptor = [d
                      for (f, d) in self._poll_descriptors
                      if f is future]
        if not descriptor:
            # no record of this future => no veto of cancel.
            # we can get here if the future is already done
            # or if polling hasn't started yet
            return True

        assert len(descriptor) == 1, "Too many poll descriptors for %s" % future

        descriptor = descriptor[0]

        try:
            return self._cancel_fn(descriptor.result)
        except Exception:
            self._log.exception("Exception during cancel on %s/%s", future, descriptor.result)
            return False

    def _run_poll_fn(self):
        with self._lock:
            descriptors = [d for (_, d) in self._poll_descriptors]

        try:
            return self._poll_fn(descriptors)
        except Exception as e:
            self._log.debug("Poll function failed", exc_info=True)
            # If poll function fails, then every future
            # depending on the poll also immediately fails.
            [d.yield_exception(e) for d in descriptors]

    def shutdown(self, wait=True):
        self._shutdown = True
        self._poll_event.set()
        self._delegate.shutdown(wait)
        if wait:
            self._log.debug("Join poll thread...")
            self._poll_thread.join(_MAX_TIMEOUT)
            self._log.debug("Joined poll thread.")


def _poll_loop(executor_ref):
    while True:
        executor = executor_ref()
        if not executor:
            break

        if executor._shutdown:
            break

        executor._log.debug("Polling...")

        next_sleep = executor._run_poll_fn()
        if not (isinstance(next_sleep, int) or isinstance(next_sleep, float)):
            next_sleep = executor._default_interval

        executor._log.debug("Sleeping...")

        poll_event = executor._poll_event
        del executor

        poll_event.wait(next_sleep)
        poll_event.clear()
