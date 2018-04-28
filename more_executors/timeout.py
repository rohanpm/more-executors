"""Create futures which must complete within a timeout or be cancelled."""
from concurrent.futures import Executor
from threading import Event, Thread, Lock
from collections import namedtuple
import logging

from monotonic import monotonic

from more_executors.map import _MapFuture
from more_executors._common import _MAX_TIMEOUT

__pdoc__ = {}
__pdoc__['TimeoutExecutor.map'] = None
__pdoc__['TimeoutExecutor.shutdown'] = None
__pdoc__['TimeoutExecutor.submit'] = None

_Job = namedtuple('_Job', ['future', 'delegate_future', 'deadline'])


class _TimeoutFuture(_MapFuture):
    def __init__(self, delegate):
        super(_TimeoutFuture, self).__init__(delegate, lambda x: x)


class TimeoutExecutor(Executor):
    """An `Executor` which delegates to another `Executor` while applying
    a timeout to each returned future.

    For any futures returned by this executor, if the future hasn't
    completed approximately within `timeout` seconds of its creation,
    an attempt will be made to cancel the future.

    Note that only a single attempt is made to cancel any future, and there
    is no guarantee that this will succeed.

    *Since version 1.7.0*
    """
    def __init__(self, delegate, timeout, logger=None):
        """Create a new executor.

        - `delegate`: the delegate executor to which callables are submitted.
        - `timeout`: timeout (in seconds) after which `future.cancel()` will be
                     invoked on any generated future which has not completed.
        - `logger`: a `Logger` used for messages from this executor
        """
        self._log = logger if logger else logging.getLogger('TimeoutExecutor')
        self._delegate = delegate
        self._timeout = timeout
        self._shutdown = False
        self._jobs = []
        self._jobs_lock = Lock()
        self._jobs_write = Event()
        self._job_thread = Thread(
            name='TimeoutExecutor', target=self._job_loop)
        self._job_thread.daemon = True
        self._job_thread.start()

    def submit(self, fn, *args, **kwargs):
        delegate_future = self._delegate.submit(fn, *args, **kwargs)
        future = _TimeoutFuture(delegate_future)
        future.add_done_callback(self._on_future_done)
        job = _Job(future, delegate_future, monotonic() + self._timeout)
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
            self._job_thread.join(_MAX_TIMEOUT)

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

    def _job_loop(self):
        while not self._shutdown:
            self._log.debug("job loop")

            with self._jobs_lock:
                (pending, overdue) = self._partition_jobs()
                self._jobs = pending

            self._log.debug("jobs: %s overdue, %s pending", len(overdue), len(pending))

            for job in overdue:
                self._do_cancel(job)

            wait_time = None
            if pending:
                earliest = min([job.deadline for job in pending])
                wait_time = max(earliest - monotonic(), 0)

            self._log.debug("Wait until %s", wait_time)
            self._jobs_write.wait(wait_time)
            self._jobs_write.clear()
