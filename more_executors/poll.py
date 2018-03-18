"""Create futures resolved by polling with a provided function."""
from concurrent.futures import Executor
from collections import namedtuple
from threading import RLock, Thread, Event
import sys
import logging

from more_executors._common import _Future

_LOG = logging.getLogger('PollExecutor')

__pdoc__ = {}
__pdoc__['PollExecutor.shutdown'] = None
__pdoc__['PollExecutor.map'] = None


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

    def cancel(self):
        with self._me_lock:
            if self.cancelled():
                return True
            if self._delegate and not self._delegate.cancel():
                return False
            if not self._executor._run_cancel_fn(self):
                return False
            self._executor._deregister_poll(self)

            out = super(_PollFuture, self).cancel()
            if out:
                self.set_running_or_notify_cancel()
        if out:
            self._me_invoke_callbacks()
        return out


PollDescriptor = namedtuple('PollDescriptor', ['result', 'yield_result', 'yield_exception'])

if sys.version_info[0] > 2:
    PollDescriptor.__doc__ = \
        """A `PollDescriptor` represents an unresolved `Future`.

        The poll function used by `more_executors.poll.PollExecutor` will be
        invoked with a list of `PollDescriptor` objects.
        """

    PollDescriptor.result.__doc__ = \
        """The result from the delegate executor's future, which should be used to
        drive the poll."""

    PollDescriptor.yield_result.__doc__ = \
        """The poll function can call this function to make the future yield the given result."""

    PollDescriptor.yield_exception.__doc__ = \
        """The poll function can call this function to make the future raise the given exception."""


class PollExecutor(Executor):
    """Instances of `PollExecutor` submit callables to a delegate `Executor`
    and resolve the returned futures via a provided poll function.

    A cancel function may also be provided to perform additional processing
    when a returned future is cancelled.

    ### **Poll function**

    The poll function has the following semantics:

    - It's called with a single argument, a list of zero or more
      `more_executors.poll.PollDescriptor` objects.

    - If the poll function can determine that a particular future should be
      completed, either successfully or in error, it should call the `yield_result`
      or `yield_exception` methods on the appropriate `PollDescriptor`.

    - If the poll function raises an exception, all futures depending on that poll
      will fail with that exception.  The poll function will be retried later.

    - If the poll function returns an int or float, it is used as the delay
      in seconds until the next poll.

    ### **Cancel function**

    The cancel function has the following semantics:

    - It's called when cancel is requested on a future returned by this executor,
      if and only if the future is currently in the list of futures being polled,
      i.e. it will not be called if the delegate future has not yet completed.

    - It's called with a single argument: the value returned by the delegate future.

    - It should return `True` if the future can be cancelled.

    - If the cancel function raises an exception, the future's cancel method will
      return `False` and a message will be logged.

    ### **Example**

    Consider a web service which executes tasks asynchronously, with an API like this:

    * To create a task: `POST https://myservice/object/:id/publish`
        * Returns an identifier for a task, such as `{"task_id": 123}`
    * To get status of a single task: `GET https://myservice/tasks/:id`
        * Returns task status, such as `{"task_id": 123, "state": "finished"}`
    * To cancel a single task: `DELETE https://myservice/tasks/:id`
    * To search for status of multiple tasks:
      `POST https://myservice/tasks/search {"task_id": [123, 456, ...]}`
        * Returns array of task statuses, such as
          `[{"task_id": 123, "state": "finished"},
            {"task_id": 456, "state": "error", "error": "..."}]`

    Imagine we want to run many tasks concurrently and monitor their status.
    Two obvious approaches include:

    * We could make a function which starts a task and polls that task until
      it completes, and have several threads run that function for different tasks.
        * This could be easily encapsulated as a future using only the executors
          from `concurrent.futures`, but is very inefficient - each task in progress
          will consume a thread for polling.
    * We could maintain a list of all outstanding tasks and implement a special-purpose
      function to wait for all of them to complete.
        * This is efficient as only one request is needed per poll interval, but since
          tasks aren't represented as futures, useful features from `concurrent.futures`
          cannot be used and different types of asynchronous work will be handled
          inconsistently.

    `PollExecutor` bridges the gap between the two approaches.  By providing a custom
    poll function, the tasks can be monitored by one thread efficiently, while at the
    same time allowing full usage of the API provided by `Future` objects.

    In this example, the poll function would look similar to this:

        def poll_tasks(poll_descriptors):
            # Collect tasks we'll need to search for
            task_ids = [d.result.get('task_id')
                        for d in poll_descriptors]

            # Search for status of these tasks
            search = {"task_id": task_ids}
            response = requests.post(
                'https://myservice/tasks/search', json=search)

            # If request failed then all outstanding futures fail
            response.raise_for_status()

            # Request passed, resolve futures accordingly
            tasks = {task.get('task_id'): task.get('state')
                    for task in response.json()}
            for d in poll_descriptors:
                task = tasks.get(d.result, {})
                state = task.get('state')
                if state == 'finished':
                    d.yield_result()
                elif state == 'error':
                    d.yield_exception(TaskFailed())

    To ensure that calling `future.cancel()` also cancels tasks on the remote service,
    we can also provide a cancel function:

        def cancel_task(task):
            task_id = task['task_id']

            # Attempt to DELETE this task
            response = requests.delete(
                'https://myservice/tasks/%s' % task_id)

            # Succeeded only if response was OK.
            # Otherwise, we may have been too late to cancel.
            return response.ok

    With the poll and cancel functions in place, futures could be created like this:

        def publish(object_id):
            response = requests.post(
                'https://myservice/object/%s/publish' % object_id)
            response.raise_for_status()
            return response.json()

        # Submit up to 4 HTTP requests at a time,
        # and poll for the returned tasks using our poll function.
        executor = Executors.\\
            threadpool(max_workers=4).\\
            with_poll(poll_tasks, cancel_task)
        futures = [executor.submit(publish, x)
                   for x in (10, 20, 30)]

        # Now we can use concurrent.futures API to get tasks as
        # the poll function determines they've completed
        for completed in as_completed(futures):
            # ...
    """

    def __init__(self, delegate, poll_fn, cancel_fn=None, default_interval=5.0):
        """Create a new executor.

        - `delegate`: `Executor` instance to which callables will be submitted
        - `poll_fn`: a polling function used to decide when futures should be resolved;
                     see the class documentation for more information
        - `cancel_fn`: a cancel function invoked when future cancel is required; see the
                       class documentation for more information
        - `default_interval`: default interval between polls (in seconds)
        """
        self._delegate = delegate
        self._default_interval = default_interval
        self._poll_fn = poll_fn
        self._cancel_fn = cancel_fn
        self._poll_descriptors = []
        self._poll_event = Event()
        self._poll_thread = Thread(name='PollExecutor', target=self._poll_loop)
        self._poll_thread.daemon = True
        self._shutdown = False
        self._lock = RLock()

        self._poll_thread.start()

    def submit(self, fn, *args, **kwargs):
        """Submit a callable.

        Returns a future which will be resolved via the poll function."""
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
            _LOG.exception("Exception during cancel on %s/%s", future, descriptor.result)
            return False

    def _run_poll_fn(self):
        with self._lock:
            descriptors = [d for (_, d) in self._poll_descriptors]
            self._poll_event.clear()

        try:
            return self._poll_fn(descriptors)
        except Exception as e:
            _LOG.debug("Poll function failed: %s", e)
            # If poll function fails, then every future
            # depending on the poll also immediately fails.
            [d.yield_exception(e) for d in descriptors]

    def _poll_loop(self):
        while not self._shutdown:
            _LOG.debug("Polling...")

            next_sleep = self._run_poll_fn()
            if not (isinstance(next_sleep, int) or isinstance(next_sleep, float)):
                next_sleep = self._default_interval

            _LOG.debug("Sleeping...")
            self._poll_event.wait(next_sleep)

    def shutdown(self, wait=True):
        self._shutdown = True
        self._poll_event.set()
        self._delegate.shutdown(wait)
        if wait:
            _LOG.debug("Join poll thread...")
            self._poll_thread.join()
            _LOG.debug("Joined poll thread.")
