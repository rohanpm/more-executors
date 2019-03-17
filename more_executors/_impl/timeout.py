from concurrent.futures import Executor
from threading import Event, Thread, Lock
from collections import namedtuple
import weakref
import logging

from monotonic import monotonic

from .map import MapFuture
from .common import MAX_TIMEOUT
from .wrap import CanCustomizeBind

LOG = logging.getLogger('TimeoutExecutor')

Job = namedtuple('Job', ['future', 'delegate_future', 'deadline'])


class TimeoutFuture(MapFuture):
    def __init__(self, delegate):
        super(TimeoutFuture, self).__init__(delegate, lambda x: x)


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
    def __init__(self, delegate, timeout, logger=None):
        """
        Parameters:

            delegate (~concurrent.futures.Executor):
                an executor to which callables are submitted

            timeout (float):
                timeout (in seconds) after which :meth:`concurrent.futures.Future.cancel()`
                will be invoked on any generated future which has not completed

            logger (~logging.Logger):
                a logger used for messages from this executor
        """
        self._log = logger if logger else LOG
        self._delegate = delegate
        self._timeout = timeout
        self._shutdown = False
        self._jobs = []
        self._jobs_lock = Lock()
        self._jobs_write = Event()

        event = self._jobs_write
        self_ref = weakref.ref(self, lambda _: event.set())

        self._job_thread = Thread(
            name='TimeoutExecutor', target=self._job_loop, args=(self_ref,))
        self._job_thread.daemon = True
        self._job_thread.start()

    def submit(self, fn, *args, **kwargs):
        return self.submit_timeout(self._timeout, fn, *args, **kwargs)

    def submit_timeout(self, timeout, fn, *args, **kwargs):
        """Like :code:`submit(fn, *args, **kwargs)`, but uses the specified
        timeout rather than this executor's default.

        .. versionadded:: 1.19.0
        """
        delegate_future = self._delegate.submit(fn, *args, **kwargs)
        future = TimeoutFuture(delegate_future)
        future.add_done_callback(self._on_future_done)
        job = Job(future, delegate_future, monotonic() + timeout)
        with self._jobs_lock:
            self._jobs.append(job)
        self._jobs_write.set()
        return future

    def shutdown(self, wait=True):
        self._log.debug("shutdown")
        self._shutdown = True
        self._jobs_write.set()
        self._delegate.shutdown(wait)
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
        self._log.debug("Cancel of %s resulted in %s", job, cancel_result)

    @classmethod
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

        if executor._shutdown:
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
