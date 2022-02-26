Polling: ``PollExecutor``
=========================

PollExecutor allows producing futures which should be resolved via a
custom poll function.


.. _poll function:

Poll function
~~~~~~~~~~~~~

The poll function has the following semantics:

- It's called with a single argument, a list of zero or more
  :class:`~more_executors.PollDescriptor` objects.

- If the poll function can determine that a particular future should be
  completed, either successfully or in error, it should call the
  :meth:`yield_result` or :meth:`yield_exception` methods on the appropriate
  :class:`~more_executors.PollDescriptor`.

- If the poll function raises an exception, all futures depending on that poll
  will fail with that exception.  The poll function will be retried later.

- If the poll function returns an int or float, it is used as the delay
  in seconds until the next poll.

.. warning::

  The poll function should avoid holding a reference to the corresponding
  :class:`~more_executors.PollExecutor`. If it holds a reference to the
  executor, invoking :meth:`~concurrent.futures.Executor.shutdown` becomes
  mandatory in order to stop the polling thread.

.. _cancel function:


Cancel function
~~~~~~~~~~~~~~~

The cancel function has the following semantics:

- It's called when cancel is requested on a future returned by this executor,
  if and only if the future is currently in the list of futures being polled,
  i.e. it will not be called if the delegate future has not yet completed.

- It's called with a single argument: the value returned by the delegate
  future.

- It should return `True` if the future can be cancelled.

- If the cancel function raises an exception, the future's cancel method will
  return `False` and a message will be logged.


Example
~~~~~~~

Consider a web service which executes tasks asynchronously, with an API like
this:

* To create a task: `POST https://myservice/object/:id/publish`

    * Returns an identifier for a task, such as `{"task_id": 123}`

* To get status of a single task: `GET https://myservice/tasks/:id`

    * Returns task status, such as `{"task_id": 123, "state": "finished"}`

* To cancel a single task: `DELETE https://myservice/tasks/:id`

* To search for status of multiple tasks:
  `POST https://myservice/tasks/search {"task_id": [123, 456, ...]}`

    * Returns array of task statuses, such as:

    .. code-block:: JSON

        [{"task_id": 123, "state": "finished"},
         {"task_id": 456, "state": "error", "error": "..."}]

Imagine we want to run many tasks concurrently and monitor their status.
Two obvious approaches include:

* We could make a function which starts a task and polls that task until
  it completes, and have several threads run that function for different tasks.

  * This could be easily encapsulated as a future using only the executors
    from :mod:`concurrent.futures`, but is very inefficient - each task in
    progress will consume a thread for polling.

* We could maintain a list of all outstanding tasks and implement a
  special-purpose function to wait for all of them to complete.

    * This is efficient as only one request is needed per poll interval, but
      since tasks aren't represented as futures, useful features from
      :mod:`concurrent.futures` cannot be used and different types of
      asynchronous work will be handled inconsistently.

:class:`~more_executors.PollExecutor` bridges the gap between the two
approaches.  By providing a custom poll function, the tasks can be monitored
by one thread efficiently, while at the same time allowing full usage of the
API provided by `Future` objects.

In this example, the poll function would look similar to this:

.. code-block:: python

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

To ensure that calling `future.cancel()` also cancels tasks on the
remote service, we can also provide a cancel function:

.. code-block:: python

    def cancel_task(task):
        task_id = task['task_id']

        # Attempt to DELETE this task
        response = requests.delete(
            'https://myservice/tasks/%s' % task_id)

        # Succeeded only if response was OK.
        # Otherwise, we may have been too late to cancel.
        return response.ok

With the poll and cancel functions in place, futures could be created
like this:

.. code-block:: python

    def publish(object_id):
        response = requests.post(
            'https://myservice/object/%s/publish' % object_id)
        response.raise_for_status()
        return response.json()

    # Submit up to 4 HTTP requests at a time,
    # and poll for the returned tasks using our poll function.
    executor = Executors.\
        threadpool(max_workers=4).\
        with_poll(poll_tasks, cancel_task)
    futures = [executor.submit(publish, x)
                for x in (10, 20, 30)]

    # Now we can use concurrent.futures API to get tasks as
    # the poll function determines they've completed
    for completed in as_completed(futures):
        # ...


.. autoclass:: more_executors.PollExecutor
   :members:

.. automethod:: more_executors.Executors.with_poll(executor, poll_fn, cancel_fn=None, default_interval=5.0, logger=None)

.. autoclass:: more_executors.PollDescriptor()
   :members:
