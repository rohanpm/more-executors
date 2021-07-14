from concurrent.futures import Executor
from threading import Thread, Lock
from collections import namedtuple
import weakref
import logging

from monotonic import monotonic

from .map import MapFuture
from .common import MAX_TIMEOUT
from .wrap import CanCustomizeBind
from .helpers import executor_loop
from .event import get_event, is_shutdown
from .logwrap import LogWrapper
from .helpers import ShutdownHelper
from .metrics import metrics, track_future

LOG = LogWrapper(logging.getLogger("TimeoutExecutor"))


Job = namedtuple("Job", ["future", "delegate_future", "deadline"])


class TimeoutExecutor(CanCustomizeBind, Executor):
    """An executor which delegates to another executor while applying
    a timeout to each returned future.

    For any futures returned by this executor, if the future hasn't
    completed approximately within `timeout` seconds of its creation,
    an attempt will be made to cancel the future.

    Note that only a single attempt is made to cancel any future, and there
    is no guarantee that this will succeed.

    .. versionadded:: 1.7.0
    """

    def __init__(self, delegate, timeout, logger=None, name="default"):
        """
        Parameters:

            delegate (~concurrent.futures.Executor):
                an executor to which callables are submitted

            timeout (float):
                timeout (in seconds) after which :meth:`concurrent.futures.Future.cancel()`
                will be invoked on any generated future which has not completed

            logger (~logging.Logger):
                a logger used for messages from this executor

            name (str):
                a name for this executor

        .. versionchanged:: 2.7.0
            Introduced ``name``.
        """
        self._log = logger if logger else LOG
        self._name = name
        self._delegate = delegate
        self._timeout = timeout
        self._shutdown = ShutdownHelper()
        self._jobs = []
        self._jobs_lock = Lock()
        self._jobs_write = get_event()

        event = self._jobs_write
        self_ref = weakref.ref(self, lambda _: event.set())

        self._job_thread = Thread(
            name="TimeoutExecutor-%s" % name, target=self._job_loop, args=(self_ref,)
        )
        self._job_thread.daemon = True
        self._job_thread.start()

        metrics.EXEC_TOTAL.labels(type="timeout", executor=self._name).inc()
        metrics.EXEC_INPROGRESS.labels(type="timeout", executor=self._name).inc()

    def submit(self, *args, **kwargs):  # pylint: disable=arguments-differ
        return self.submit_timeout(self._timeout, *args, **kwargs)

    def submit_timeout(self, timeout, fn, *args, **kwargs):
        """Like :code:`submit(fn, *args, **kwargs)`, but uses the specified
        timeout rather than this executor's default.

        .. versionadded:: 1.19.0
        """
        with self._shutdown.ensure_alive():
            delegate_future = self._delegate.submit(fn, *args, **kwargs)
            future = MapFuture(delegate_future)
            track_future(future, type="timeout", executor=self._name)

            future.add_done_callback(self._on_future_done)
            job = Job(future, delegate_future, monotonic() + timeout)
            with self._jobs_lock:
                self._jobs.append(job)
            self._jobs_write.set()
            return future

    def shutdown(self, wait=True, **_kwargs):
        if self._shutdown():
            self._log.debug("shutdown")
            metrics.EXEC_INPROGRESS.labels(type="timeout", executor=self._name).dec()
            self._jobs_write.set()
            self._delegate.shutdown(wait, **_kwargs)
            if wait:
                self._job_thread.join(MAX_TIMEOUT)

    def _partition_jobs(self):
        pending = []
        overdue = []
        now = monotonic()
        for job in self._jobs:
            if job.future.done():
                self._log.debug("Discarding job for completed future: %s", job)
            elif job.deadline < now:
                overdue.append(job)
            else:
                pending.append(job)
        return (pending, overdue)

    def _on_future_done(self, future):
        self._log.debug("Waking thread for %s", future)
        self._jobs_write.set()

    def _do_cancel(self, job):
        self._log.debug("Attempting cancel: %s", job)
        cancel_result = job.future.cancel()
        if cancel_result:
            metrics.TIMEOUT.labels(executor=self._name).inc()
        self._log.debug("Cancel of %s resulted in %s", job, cancel_result)

    @classmethod
    @executor_loop
    def _job_loop(cls, executor_ref):
        while True:
            (event, wait_time) = cls._job_loop_iter(executor_ref())
            if not event:
                break
            event.wait(wait_time)
            event.clear()

    @classmethod
    def _job_loop_iter(cls, executor):
        if not executor:
            LOG.debug("Executor was collected")
            return (None, None)

        if executor._shutdown.is_shutdown or is_shutdown():
            executor._log.debug("Executor was shut down")
            return (None, None)

        executor._log.debug("job loop")

        with executor._jobs_lock:
            (pending, overdue) = executor._partition_jobs()
            executor._jobs = pending

        executor._log.debug("jobs: %s overdue, %s pending", len(overdue), len(pending))

        for job in overdue:
            executor._do_cancel(job)

        wait_time = None
        if pending:
            earliest = min([job.deadline for job in pending])
            wait_time = max(earliest - monotonic(), 0)

        executor._log.debug("Wait until %s", wait_time)
        return (executor._jobs_write, wait_time)
