User Guide
==========

.. _base executors:

Base executors
--------------

These methods on the :class:`more_executors.Executors` class
create standalone :class:`~concurrent.futures.Executor`
instances which may serve as the basis of `composing executors`_.

    :meth:`~more_executors.Executors.thread_pool`
        creates a new :class:`~concurrent.futures.ThreadPoolExecutor`
        to execute callables in threads.

    :meth:`~more_executors.Executors.process_pool`
        creates a new :class:`~concurrent.futures.ProcessPoolExecutor`
        to execute callables in processes.

    :meth:`~more_executors.Executors.sync`
        creates a new :class:`~more_executors.sync.SyncExecutor`
        to execute callables in the calling thread.

Example:

.. code-block:: python

    from more_executors import Executors
    with Executors.thread_pool() as executor:
        future = executor.submit(requests.get, 'https://github.com/rohanpm/more-executors')


.. _composing executors:

Composing executors
-------------------

Executors produced by this module can be customized by chaining a series of
`with_*` methods. This may be used to compose different behaviors for specific
use-cases.

Methods for composition are provided for all implemented executors:

    :meth:`~more_executors.Executors.with_map`
        transform the output of a future, synchronously
    :meth:`~more_executors.Executors.with_flat_map`
        transform the output of a future, asynchronously
    :meth:`~more_executors.Executors.with_retry`
        retry failing futures
    :meth:`~more_executors.Executors.with_poll`
        resolve failing futures via a custom poll function
    :meth:`~more_executors.Executors.with_timeout`
        cancel unresolved futures after a timeout
    :meth:`~more_executors.Executors.with_throttle`
        limit the number of concurrently executing futures
    :meth:`~more_executors.Executors.with_cancel_on_shutdown`
        cancel any pending futures on executor shutdown
    :meth:`~more_executors.Executors.with_asyncio`
        bridge between :mod:`concurrent.futures` and :mod:`asyncio`

Example:

.. code-block:: python

    # Run in up to 4 threads, retry on failure, transform output values
    executor = Executors.thread_pool(max_workers=4). \
        with_map(lambda response: response.json()). \
        with_retry()
    responses = [executor.submit(requests.get, url)
                 for url in urls]

Keep in mind that the order in which executors are composed is significant.
For example, these two composition sequences have different effects:

.. code-block:: python

    Executors.sync().with_retry().with_throttle(4)

In this example, if 4 callables have failed and retries are currently pending,
throttling takes effect, and any additional callables will be enqueued until at
least one of the earlier callables has completed (or exhausted all retry
attempts).

.. code-block:: python

    Executors.sync().with_throttle(4).with_retry()

In this example, an unlimited number of futures may be failed and awaiting
retries. The throttling in this example has no effect, since a
:class:`~more_executors.sync.SyncExecutor` is intrinsically throttled to
a single pending future.


Binding callables to executors
------------------------------

The :meth:`~more_executors.Executors.bind` method produces a callable which is
bound to a specific executor.

This is illustrated by the following example.
Consider this code to fetch data from a list of URLs expected to provide JSON,
with up to 8 concurrent requests and retries on failure, without using
:meth:`bind`:

.. code-block:: python

    executor = Executors.thread_pool(max_workers=8). \
        with_map(lambda response: response.json()). \
        with_retry()

    futures = [executor.submit(requests.get, url)
                for url in urls]

The following code using :meth:`bind` is functionally
equivalent:

.. code-block:: python

    async_get = Executors.thread_pool(max_workers=8). \
        bind(requests.get). \
        with_map(lambda response: response.json()). \
        with_retry()

    futures = [async_get(url) for url in urls]

The latter example using :meth:`bind` is more readable because the order of
the calls to set up the pipeline more closely reflects the order in
which the pipeline executes at runtime.

In contrast, without using :meth:`bind`, the *first* step of the pipeline -
:meth:`requests.get` - appears at the *end* of the code, which is harder
to follow.

:meth:`~more_executors.Executors.flat_bind` is also provided for use with
callables returning a future. It behaves in the same way as :meth:`bind`,
but avoids returning a nested future.


Usage of threads
----------------

Several executors internally make use of threads. Thus, executors should be
considered relatively heavyweight: creating dozens of executors within a
process is probably fine, creating thousands is possibly not.

Callbacks added by :meth:`~concurrent.futures.Future.add_done_callback` may
be invoked from any thread and should avoid any slow blocking operations.

All provided executors are thread-safe with the exception of the
:meth:`~concurrent.futures.Executor.shutdown` method, which should be called
from one thread only.


Executor shutdown
-----------------

Shutting down an executor will also shut down all wrapped executors.

In the example below, any threads created by the
:class:`~concurrent.futures.ThreadPoolExecutor`, as well as the thread
created by the :class:`~more_executors.retry.RetryExecutor`, will be joined
at the end of the `with` block:

.. code-block:: python

    executor = Executors.thread_pool(). \
        with_map(check_result). \
        with_retry()

    with executor:
        do_something(executor)
        do_other_thing(executor)

Note this implies that sharing of executors needs to be done carefully.
For example, this code is broken:

.. code-block:: python

    executor = Executors.thread_pool().with_map(check_result)

    # Only need retries on this part
    with executor.with_retry() as retry_executor:
        do_flaky_something(retry_executor)

    # BUG: don't do this!
    # The thread pool executor was already shut down, so this won't work.
    with executor:
        do_something(executor)

Shutting down executors is optional and is not necessary to (eventually)
reclaim resources.
