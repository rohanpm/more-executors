from concurrent.futures import Executor
from threading import RLock, Thread, Event
import weakref
import logging

from .common import _Future, MAX_TIMEOUT, copy_exception, copy_future_exception
from .wrap import CanCustomizeBind


class PollFuture(_Future):
    def __init__(self, delegate, executor):
        super(PollFuture, self).__init__()
        self._delegate = delegate
        self._executor = executor
        self._delegate.add_done_callback(self._delegate_resolved)
        self.add_done_callback(self._clear_executor)

    def _delegate_resolved(self, delegate):
        assert delegate is self._delegate, \
            "BUG: called with %s, expected %s" % (delegate, self._delegate)

        if delegate.cancelled():
            return
        elif delegate.exception():
            copy_future_exception(delegate, self)
        else:
            self._executor._register_poll(self, self._delegate)

    def _clear_delegate(self):
        with self._me_lock:
            self._delegate = None

    @classmethod
    def _clear_executor(cls, future):
        future._executor._deregister_poll(future)
        future._executor = None

    def set_result(self, result):
        with self._me_lock:
            if self.done():
                return
            super(PollFuture, self).set_result(result)
        self._me_invoke_callbacks()

    def set_exception(self, exception):
        with self._me_lock:
            # We can't get here because we always try set_exception_info first,
            # which succeeds if done() is true, in which case we won't fall
            # back to set_exception.
            # if self.done():
            #    return
            super(PollFuture, self).set_exception(exception)
        self._me_invoke_callbacks()

    def set_exception_info(self, exception, traceback):
        # For python2 compat.
        # pylint: disable=no-member
        with self._me_lock:
            if self.done():
                return
            super(PollFuture, self).set_exception_info(exception, traceback)
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
        executor = self._executor
        return executor and executor._run_cancel_fn(self)


class PollDescriptor(object):
    """Represents an unresolved :class:`~concurrent.futures.Future`.

    The poll function used by :class:`PollExecutor` will be
    invoked with a list of PollDescriptor objects.
    """

    def __init__(self, future, result):
        self.__future = future
        self.__result = result

    @property
    def result(self):
        """The result from the delegate executor's future, which should be used to
        drive the poll."""
        return self.__result

    def yield_result(self, result):
        """The poll function can call this function to make the future yield the given result.

        Arguments:
            result (object):
                a result to be returned by the future associated with this descriptor
        """

        self.__future.set_result(result)

    def yield_exception(self, exception, traceback=None):
        """The poll function can call this function to make the future raise the given exception.

        Arguments:
           exception (Exception):
               An exception to be returned or raised by the future associated with this
               descriptor
           traceback (traceback):
               An optional associated traceback. This argument only has an effect on python 2.x,
               where exception objects do not include a traceback.
        """

        copy_exception(self.__future, exception, traceback)


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
        return PollFuture(delegate_future, self)

    def _register_poll(self, future, delegate_future):
        descriptor = PollDescriptor(future, delegate_future.result())
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
            self._poll_thread.join(MAX_TIMEOUT)
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
