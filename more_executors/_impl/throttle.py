from concurrent.futures import Executor
from threading import Thread, Lock
from collections import namedtuple, deque
from functools import partial
import logging
import weakref

from .common import MAX_TIMEOUT
from .wrap import CanCustomizeBind
from .map import MapFuture
from .helpers import executor_loop, ShutdownHelper
from .event import get_event, is_shutdown
from .logwrap import LogWrapper

from .metrics import metrics, track_future


class ThrottleFuture(MapFuture):
    def __init__(self, executor):
        self._executor = executor
        super(ThrottleFuture, self).__init__(delegate=None, map_fn=lambda x: x)
        self.add_done_callback(self._clear_executor)

    def _me_cancel(self):
        if self._delegate:
            return self._delegate.cancel()
        executor = self._executor
        return executor and executor._do_cancel(self)

    @classmethod
    def _clear_executor(cls, future):
        future._executor = None


ThrottleJob = namedtuple("ThrottleJob", ["future", "fn", "args", "kwargs"])


class AtomicInt(object):
    def __init__(self):
        self.value = 0
        self.lock = Lock()

    def decr(self):
        with self.lock:
            self.value -= 1

    def incr(self):
        with self.lock:
            self.value += 1


class ThrottleExecutor(CanCustomizeBind, Executor):
    """An executor which delegates to another executor while enforcing
    a limit on the number of futures running concurrently.

    - Callables are submitted to the delegate executor, from a different
      thread than the calling thread.

    - Where `count` is used to initialize this executor, if there
      are already `count` futures submitted to the delegate executor and not
      yet :meth:`~concurrent.futures.Future.done`, additional callables will
      be queued and only submitted to the delegate executor once there are
      less than `count` futures in progress.

    .. versionadded:: 1.9.0
    """

    def __init__(self, delegate, count, logger=None, name="default"):
        """
        Parameters:
            delegate (~concurrent.futures.Executor):
                an executor to which callables will be submitted

            count (int, callable):
                int:
                    maximum number of concurrently running futures.
                callable:
                    a callable which returns an ``int`` (or ``None``, to indicate
                    no throttling).

                    The callable will be invoked each time this executor needs
                    to decide whether to throttle futures; this may be used
                    to implement dynamic throttling.

                    .. versionadded:: 2.5.0

            logger (~logging.Logger):
                a logger used for messages from this executor

            name (str):
                a name for this executor

        .. versionchanged:: 2.7.0
            Introduced ``name``.
        """
        self._log = LogWrapper(
            logger if logger else logging.getLogger("ThrottleExecutor")
        )
        self._name = name
        self._delegate = delegate
        self._to_submit = deque()
        self._lock = Lock()
        self._event = get_event()
        self._running_count = AtomicInt()
        self._throttle = count if callable(count) else lambda: count
        self._last_throttle = self._throttle()
        self._shutdown = ShutdownHelper()

        event = self._event
        self_ref = weakref.ref(self, lambda _: event.set())

        metrics.EXEC_INPROGRESS.labels(type="throttle", executor=self._name).inc()
        metrics.EXEC_TOTAL.labels(type="throttle", executor=self._name).inc()

        self._thread = Thread(
            name="ThrottleExecutor-%s" % name, target=_submit_loop, args=(self_ref,)
        )
        self._thread.daemon = True
        self._thread.start()

    def submit(self, fn, *args, **kwargs):  # pylint: disable=arguments-differ
        with self._shutdown.ensure_alive():
            out = ThrottleFuture(self)
            track_future(out, type="throttle", executor=self._name)

            job = ThrottleJob(out, fn, args, kwargs)
            with self._lock:
                self._to_submit.append(job)
                metrics.THROTTLE_QUEUE.labels(executor=self._name).inc()
                self._log.debug("Enqueued: %s", job)
            self._event.set()
            return out

    def shutdown(self, wait=True, **_kwargs):
        if self._shutdown():
            self._log.debug("Shutting down")
            metrics.EXEC_INPROGRESS.labels(type="throttle", executor=self._name).dec()
            self._delegate.shutdown(wait, **_kwargs)
            self._event.set()
            if wait:
                self._thread.join(MAX_TIMEOUT)

    def _eval_throttle(self):
        try:
            self._last_throttle = self._throttle()
        except Exception:
            self._log.exception(
                "Error evaluating throttle count via %r", self._throttle
            )

        return self._last_throttle

    def _do_submit(self, job):
        delegate_future = self._delegate.submit(job.fn, *job.args, **job.kwargs)
        self._log.debug("Submitted %s yielding %s", job, delegate_future)

        delegate_future.add_done_callback(
            partial(
                self._delegate_future_done, self._log, self._running_count, self._event
            )
        )
        job.future._set_delegate(delegate_future)

    def _do_cancel(self, future):
        with self._lock:
            for job in self._to_submit:
                if job.future is future:
                    self._to_submit.remove(job)
                    self._log.debug("Cancelled %s", job)
                    return True
        self._log.debug("Could not find for cancel: %s", future)
        return False

    @classmethod
    def _delegate_future_done(cls, log, running_count, event, future):
        # Whenever an inner future completes, the thread should wake up
        # in case there's something to be submitted
        log.debug("Delegate future done: %s", future)
        running_count.decr()
        event.set()


def _submit_loop_iter(executor):
    if not executor:
        return

    if executor._shutdown.is_shutdown or is_shutdown():
        return

    throttle = executor._eval_throttle()
    to_submit = []
    with executor._lock:
        while executor._to_submit:
            if throttle is not None and (executor._running_count.value >= throttle):
                executor._log.debug("Throttled")
                break
            job = executor._to_submit.popleft()
            executor._log.debug("Will submit: %s", job)
            to_submit.append(job)

            # While not actually running yet, we've committed to running it, so...
            executor._running_count.incr()
            metrics.THROTTLE_QUEUE.labels(executor=executor._name).dec()

        executor._log.debug(
            "Submitting %s, throttling %s", len(to_submit), len(executor._to_submit)
        )

    for job in to_submit:
        executor._do_submit(job)

    # Because the throttle count is dynamic, we should wake up at some point in
    # the future to re-check throttle, even if no other events occurred.
    # If there's nothing running at all, we should do this sooner, because
    # there won't be any events from completing futures.
    return executor._event, 30.0 if executor._running_count.value else 2.0


@executor_loop
def _submit_loop(executor_ref):
    while True:
        result = _submit_loop_iter(executor_ref())
        if not result:
            break

        (event, wait_time) = result
        event.wait(wait_time)
        event.clear()
