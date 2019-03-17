from concurrent.futures import Executor
from threading import RLock, Thread, Event
import logging
import weakref

from monotonic import monotonic

from .common import _Future, MAX_TIMEOUT, copy_future_exception
from .wrap import CanCustomizeBind


class RetryPolicy(object):
    """Instances of this class may be supplied to :class:`RetryExecutor`
    to customize the retry behavior.

    This base class will never retry.  See :class:`ExceptionRetryPolicy` for
    a general-purpose implementation."""

    def should_retry(self, attempt, future):
        """
        Parameters:
            attempt (int): number of times the future has been attempted; starts counting at 1
            future (~concurrent.futures.Future): a completed future

        Returns:
            bool:
                True if and only if a future should be retried.
        """
        return False

    def sleep_time(self, attempt, future):
        """
        Parameters:
            attempt (int): number of times the future has been attempted; starts counting at 1
            future (~concurrent.futures.Future): a completed future

        Returns:
            float:
                The amount of time (in seconds) to delay before the next
                attempt at running a future.
        """
        return 0


class ExceptionRetryPolicy(RetryPolicy):
    """Retries on any exceptions under the given base class(es),
    up to a fixed number of attempts, with an exponential
    backoff between each attempt."""

    def __init__(self, **kwargs):
        """
        Parameters:
            max_attempts (int): maximum number of times a callable should be attempted
            exponent (float): exponent used for backoff, e.g. 2.0 will result in a delay
                              which doubles between each attempt
            sleep (float): base value for delay between attempts in seconds, e.g. 1.0
                           will delay by one second between first two attempts
            max_sleep (float): maximum delay between attempts, in seconds
            exception_base (type, list(type)): future will be retried if (and only if)
                            it raises an exception inheriting from one of these classes

        All parameters are optional; reasonable defaults apply when omitted.
        """
        self._max_attempts = kwargs.get('max_attempts', 3)
        self._exponent = kwargs.get('exponent', 2.0)
        self._sleep = kwargs.get('sleep', 1.0)
        self._max_sleep = kwargs.get('max_sleep', 120)
        self._exception_base = kwargs.get('exception_base', Exception)
        if isinstance(self._exception_base, type):
            self._exception_base = [self._exception_base]

    def should_retry(self, attempt, future):
        exception = future.exception()
        if not exception:
            return False
        if attempt >= self._max_attempts:
            return False
        for klass in self._exception_base:
            if isinstance(exception, klass):
                return True
        return False

    def sleep_time(self, attempt, future):
        return min(self._sleep * (self._exponent ** attempt), self._max_sleep)


class RetryJob(object):
    def __init__(self, policy, delegate_future, future,
                 attempt, when, fn, args, kwargs):
        self.policy = policy
        self.delegate_future = delegate_future
        self.future = future
        self.attempt = attempt
        self.when = when
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.stop_retry = False


class RetryFuture(_Future):

    def __init__(self, executor):
        super(RetryFuture, self).__init__()
        self.delegate_future = None
        self._executor = executor
        self.add_done_callback(self._clear_executor)

    def running(self):
        with self._me_lock:
            if self.done():
                return False
            # Note that if we are not "done", but the delegate future is "done",
            # we consider ourselves as running - this should mean the delegate
            # future completed but callbacks haven't finished yet (and in fact,
            # we might decide to retry)
            if self.delegate_future:
                return self.delegate_future.running() or self.delegate_future.done()
        return False

    def _clear_delegate(self):
        with self._me_lock:
            self.delegate_future = None

    @classmethod
    def _clear_executor(cls, future):
        with future._me_lock:
            future._executor = None

    def __terminate_via(self, method, *args, **kwargs):
        with self._me_lock:
            self._clear_delegate()
            method(*args, **kwargs)
        self._me_invoke_callbacks()

    def set_result(self, result):
        self.__terminate_via(super(RetryFuture, self).set_result, result)

    def set_exception(self, exception):
        self.__terminate_via(super(RetryFuture, self).set_exception, exception)

    def set_exception_info(self, exception, traceback):
        # For python2 compat.
        # pylint: disable=no-member
        self.__terminate_via(
            super(RetryFuture, self).set_exception_info,
            exception, traceback)

    def _me_cancel(self):
        executor = self._executor
        return executor and executor._cancel(self)


class RetryExecutor(CanCustomizeBind, Executor):
    """An executor which delegates to another executor while adding
    implicit retry behavior.

    - Callables are submitted to the delegate executor, and may be
      submitted more than once if retries are required.

    - The callables may be submitted to that executor from a different
      thread than the calling thread.

    - Cancelling is supported if the delegate executor allows it.

    - Cancelling between retries is always supported.

    - Attempting to cancel a future prevents any more retries, regardless
      of whether the cancel succeeds.

    - The returned futures from this executor are only resolved or
      failed once the callable either succeeded, or all retries
      were exhausted.  This includes activation of the done callback.

    - This executor is thread-safe.
    """

    def __init__(self, delegate, retry_policy=None, logger=None, **kwargs):
        """
        Parameters:

            delegate (~concurrent.futures.Executor):
                executor to which callables will be submitted

            retry_policy (RetryPolicy):
                policy used to determine when futures shall be retried; if omitted,
                an :class:`ExceptionRetryPolicy` is used, supplied with keyword
                arguments to this constructor

            logger (~logging.Logger):
                a logger used for messages from this executor
        """
        self._log = logger if logger else logging.getLogger('RetryExecutor')
        self._delegate = delegate
        self._default_retry_policy = retry_policy or ExceptionRetryPolicy(**kwargs)
        self._jobs = []
        self._submit_event = Event()

        event = self._submit_event
        self_ref = weakref.ref(self, lambda _: event.set())
        self._submit_thread = Thread(
            name='RetryExecutor', target=_submit_loop, args=(self_ref,))
        self._submit_thread.daemon = True

        self._shutdown = False
        self._lock = RLock()

        self._submit_thread.start()

    def shutdown(self, wait=True):
        self._log.debug("Shutting down.")
        self._shutdown = True
        self._wake_thread()
        self._delegate.shutdown(wait)
        if wait:
            self._log.debug("Waiting for thread")
            self._submit_thread.join(MAX_TIMEOUT)
        self._log.debug("Shutdown complete")

    def submit(self, fn, *args, **kwargs):
        return self.submit_retry(
            self._default_retry_policy, fn, *args, **kwargs)

    def submit_retry(self, retry_policy, fn, *args, **kwargs):
        """Submit a callable with a specific retry policy.

        Parameters:
            retry_policy (RetryPolicy): a policy which is used for this call only
        """
        future = RetryFuture(self)

        job = RetryJob(retry_policy, None, future, 0,
                       monotonic(), fn, args, kwargs)
        self._append_job(job)

        # Let the submit thread know it should wake up to check for new jobs
        self._wake_thread()

        self._log.debug("Returning future %s", future)
        return future

    def _wake_thread(self):
        self._submit_event.set()

    def _get_next_job(self):
        # Find and return the next job to be executed, if any.
        # This means a job with when < now, or if there's none,
        # then the job with the minimum value of when.
        min_job = None
        now = monotonic()
        for job in self._jobs:
            if job.delegate_future:
                # It's already running, skip
                continue
            if job.when <= now:
                # job is overdue, just do it
                return job
            elif not min_job:
                min_job = job
            elif job.when < min_job.when:
                min_job = job
        return min_job

    def _submit_now(self, job):
        # Pop job since we'll replace it.
        # We need to hold the lock for the entire duration so that other
        # threads won't see _jobs between our removal and re-add of the job
        with job.future._me_lock:
            with self._lock:
                self._pop_job(job)

                # We need the future's lock now too, because someone could
                # call cancel after this check and before we submit.
                if job.future.done():
                    self._log.debug(
                        "future done %s - not submitting to delegate",
                        job.future)
                    return

                delegate_future = self._delegate.submit(
                    job.fn, *job.args, **job.kwargs)
                job.future.delegate_future = delegate_future

                new_job = RetryJob(
                    job.policy,
                    delegate_future,
                    job.future,
                    job.attempt + 1,
                    None,
                    job.fn, job.args, job.kwargs
                )
                self._append_job(new_job)
                self._log.debug("Submitted: %s", new_job)

        delegate_future.add_done_callback(self._delegate_callback)
        self._wake_thread()

    def _pop_job(self, job):
        with self._lock:
            for idx, pending in enumerate(self._jobs):
                if pending is job:
                    return self._jobs.pop(idx)

    def _append_job(self, job):
        with self._lock:
            self._jobs.append(job)

    def _retry(self, job, sleep_time):
        self._log.debug("Will retry: %s", job)

        with self._lock:
            self._pop_job(job)
            new_job = RetryJob(
                job.policy,
                None,
                job.future,
                job.attempt,
                monotonic() + sleep_time,
                job.fn,
                job.args,
                job.kwargs
            )
            self._append_job(new_job)

        self._wake_thread()

    def _cancel(self, future):
        found_job = None

        with self._lock:
            for idx, job in enumerate(self._jobs):
                if job.future is future:
                    self._log.debug("Try cancel: %s", job)

                    if not job.delegate_future:
                        self._log.debug("Successful cancel - no delegate: %s", job)
                        self._jobs.pop(idx)
                        return True

                    found_job = job
                    break

        # This shouldn't be possible.
        # - Future holds a lock on itself, and has checked that it's not already done
        # - The only other path for removing a job is in delegate_callback, but the
        #   job is only removed *after* set_result/set_exception which would wait
        #   for the future's lock.
        assert found_job, "Cancel called on orphan %s" % future

        # Whether or not we can successfully cancel, the request to cancel
        # means that we don't want to retry any more.
        found_job.stop_retry = True

        self._log.debug("Try cancel delegate: %s", found_job)

        if found_job.delegate_future.cancel():
            self._log.debug("Successful cancel: %s", found_job)
            future._clear_delegate()
            # Don't remove from _jobs here,
            # the callback attached to delegate_future was expected
            # to take care of that
            return True

        self._log.debug("Could not cancel: %s", found_job)
        return False

    def _delegate_callback(self, delegate_future):
        assert delegate_future.done(), \
            "BUG: callback invoked while future not done!"

        self._log.debug("Callback activated for %s", delegate_future)

        found_job = None
        for job in self._jobs[:]:
            if job.delegate_future == delegate_future:
                found_job = job
                break

        # Callbacks are only installed after a job is added, and this is
        # the only place a job with a delegate associated will be removed,
        # thus it should not be possible for a job to be missing.
        assert found_job, ("BUG: no job associated with delegate %s" % delegate_future)

        if delegate_future.cancelled():
            # nothing to do, retrying on cancel is not allowed
            self._log.debug("Delegate was cancelled: %s", delegate_future)
            return

        if found_job.stop_retry:
            should_retry = False
        else:
            should_retry = found_job.policy.should_retry(found_job.attempt, delegate_future)

        if should_retry:
            sleep_time = found_job.policy.sleep_time(found_job.attempt, delegate_future)
            self._retry(found_job, sleep_time)
            return

        self._log.debug("Finalizing %s", found_job)

        exception = delegate_future.exception()
        if exception:
            result = None
        else:
            result = delegate_future.result()

        # OK, it won't be retried.  Resolve the future.
        if exception:
            copy_future_exception(delegate_future, found_job.future)
        else:
            found_job.future.set_result(result)

        self._pop_job(found_job)

        self._log.debug("Finalized %s", found_job)


def _submit_loop(executor_ref):
    # Runs in a separate thread continuously submitting to the delegate
    # executor until no jobs are ready, or waiting until next job is ready
    while True:
        executor = executor_ref()
        if not executor:
            break

        if executor._shutdown:
            break

        executor._log.debug("_submit_loop iter")

        with executor._lock:
            job = executor._get_next_job()

        if not job:
            executor._log.debug("No jobs at all. Waiting...")
            event = executor._submit_event
            del executor
            _submit_wait(event)
            continue

        now = monotonic()
        if job.when <= now:
            # Can submit immediately and check for next job
            executor._submit_now(job)
            continue

        # There is nothing to submit immediately.
        # Sleep until either:
        # - reaching the time of the nearest job, or...
        # - woken up by condvar
        delta = job.when - now
        executor._log.debug("No ready job.  Waiting: %s", delta)
        event = executor._submit_event
        del executor
        del job
        _submit_wait(event, delta)


def _submit_wait(event, timeout=None):
    event.wait(timeout)
    event.clear()
