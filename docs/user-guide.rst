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
        creates a new :class:`~more_executors.SyncExecutor`
        to execute callables in the calling thread.

Example:

.. code-block:: python

    from more_executors import Executors
    with Executors.thread_pool(name='web-client') as executor:
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
        resolve futures via a custom poll function
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
    executor = Executors.thread_pool(max_workers=4, name='web-client'). \
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
:class:`~more_executors.SyncExecutor` is intrinsically throttled to
a single pending future.

.. _naming executors:

Naming executors
----------------

All executors accept an optional ``name`` argument, an arbitrary string.
Setting the ``name`` when creating an executor has the following effects:

- If the executor creates any threads, the thread name will include the
  specified value.

- The name will be used as ``executor`` label on any :ref:`metrics`
  associated with the executor.

When creating chained executors via the ``with_*`` methods
(see :ref:`composing executors`), names automatically propagate through
the chain:

.. code-block:: python

    Executors.thread_pool(name='svc-client').with_retry().with_throttle(4)

In the above example, three executors are created and all of them are
given the name ``svc-client``.


Composing futures
-----------------

A series of functions are provided for creating and composing
:class:`~concurrent.future.Future` objects.  These functions
may be used standalone, or in conjunction with the Executor
implementations in ``more-executors``.

+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| Function                                   | Signature                                                            | Description                          |
+============================================+======================================================================+======================================+
| :meth:`~more_executors.f_return`           | X                                                                    | wrap any value in a future           |
|                                            |  ⟶ Future<X>                                                         |                                      |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_return_error`     | `n/a`                                                                | wrap any exception in a future       |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_return_cancelled` | `n/a`                                                                | get a cancelled future               |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_apply`            | Future<fn<A[,B[,...]]⟶R>>, Future<A>[, Future<B>[, ...]]             |                                      |
|                                            |   ⟶ Future<R>                                                        | apply a function in the future       |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_or`               | Future<A>[, Future<B>[, ...]]                                        |                                      |
|                                            |   ⟶ Future<A|B|...>                                                  | boolean ``OR``                       |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_and`              | Future<A>[, Future<B>[, ...]]                                        |                                      |
|                                            |   ⟶ Future<A|B|...>                                                  | boolean ``AND``                      |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_zip`              | Future<A>[, Future<B>[, ...]]                                        |                                      |
|                                            |   ⟶ Future<A[, B[, ...]]>                                            | combine futures into a tuple         |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_map`              | Future<A>, fn<A⟶B>                                                   | transform output value of a future   |
|                                            |   ⟶ Future<B>                                                        | via a blocking function              |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_flat_map`         | Future<A>, fn<A⟶Future<B>>                                           | transform output value of a future   |
|                                            |   ⟶ Future<B>                                                        | via a non-blocking function          |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_traverse`         | fn<A⟶Future<B>>, iterable<A>                                         | run non-blocking function over       |
|                                            |   ⟶ Future<list<B>>                                                  | iterable                             |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_sequence`         | list<Future<X>>                                                      | convert list of futures to a future  |
|                                            |   ⟶ Future<list<X>>                                                  | of list                              |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_nocancel`         | Future<X>                                                            | make a future unable to be cancelled |
|                                            |   ⟶ Future<X>                                                        |                                      |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_proxy`            | Future<X>                                                            | make a future proxy calls to the     |
|                                            |   ⟶ Future<X>                                                        | future's result                      |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+
| :meth:`~more_executors.f_timeout`          | Future<X>, float                                                     | make a future cancel itself after a  |
|                                            |   ⟶ Future<X>                                                        | timeout has elapsed                  |
+--------------------------------------------+----------------------------------------------------------------------+--------------------------------------+


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
created by the :class:`~more_executors.RetryExecutor`, will be joined
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

Generally, shutting down executors is optional and is not necessary to
(eventually) reclaim resources.

However, where executors accept caller-provided code (such as the polling
function to :class:`~more_executors.PollExecutor` or the retry
policy to :class:`~more_executors.RetryExecutor`), it is easy to
accidentally create a circular reference between the provided code and the
executor. When this happens, it will no longer be possible for the garbage
collector to clean up the executor's resources automatically and a thread
leak may occur. If in doubt, call
:meth:`~concurrent.futures.Executor.shutdown`.

.. _metrics:

Prometheus metrics
------------------

This library automatically collects `Prometheus <https://prometheus.io/>`_
metrics if the ``prometheus_client`` Python module is available.
The feature is disabled when this module is not installed or if the
``MORE_EXECUTORS_PROMETHEUS`` environment variable is set to ``0``.

If you want to ensure that ``more-executors`` is installed along with
all prometheus dependencies, you may request the 'prometheus' extras,
as in example:

.. code-block::

    pip install more-executors[prometheus]

The library only collects metrics; it does not expose them.
You must use ``prometheus_client`` to expose metrics in the most
appropriate manner when integrating this library with your tool or service.
Here is a simple example to dump metrics to a file:

.. code-block:: python

    import prometheus_client
    prometheus_client.write_to_textfile('metrics.txt')


The following metrics are available:

    ``more_executors_exec_inprogress``
        A *gauge* for the number of executors currently in use.

        "In use" means an executor has been created and ``shutdown()`` not
        yet called. Incorrect usage of ``shutdown()`` (e.g. calling more than
        once) will lead to inaccurate data.

    ``more_executors_exec_total``
        A *counter* for the total number of executors created.

    ``more_executors_future_inprogress``
        A *gauge* for the number of futures currently in progress.

        "In progress" means a future has been created and not yet reached
        a terminal state.

    ``more_executors_future_total``
        A *counter* for the total number of futures created.

    ``more_executors_future_cancel_total``
        A *counter* for the total number of futures cancelled.

    ``more_executors_future_error_total``
        A *counter* for the total number of futures resolved with an exception.

    ``more_executors_future_time_total``
        A *counter* for the total execution time (in seconds) of futures.

        The execution time of a future is the period between the
        creation and resolution of a future.

    ``more_executors_poll_total``
        A *counter* for the total number of times a :ref:`poll function` was
        invoked.

    ``more_executors_poll_error_total``
        A *counter* for the total number of times a :ref:`poll function`
        raised an exception.

    ``more_executors_poll_time_total``
        A *counter* for the total execution time (in seconds) of
        :ref:`poll function` calls.

    ``more_executors_retry_total``
        A *counter* for the total number of times a future was retried
        by :class:`~more_executors.RetryExecutor`.

    ``more_executors_retry_queue``
        A *gauge* for the current queue size of a
        :class:`~more_executors.RetryExecutor` (i.e. the
        number of futures currently waiting to retry).

    ``more_executors_retry_delay_total``
        A *counter* for the total time (in seconds) spent waiting to
        retry futures via :class:`~more_executors.RetryExecutor`.

    ``more_executors_throttle_queue``
        A *gauge* for the current queue size of a
        :class:`~more_executors.ThrottleExecutor` (i.e. the number of futures
        not yet able to start due to throttling).

    ``more_executors_timeout_total``
        A *counter* for the total number of futures cancelled due to timeout
        via :class:`~more_executors.TimeoutExecutor` or
        :func:`~more_executors.f_timeout`.

        Only successfully cancelled futures are included.

    ``more_executors_shutdown_cancel_total``
        A *counter* for the total number of futures cancelled due to executor
        shutdown via :class:`~more_executors.CancelOnShutdownExecutor`.

        Only successfully cancelled futures are included.

Metrics include the following labels:

    ``type``
        The type of executor or future in use; e.g. ``map``, ``retry``,
        ``poll``.

    ``executor``
        Name of executor (see :ref:`Naming executors`).

        Executors created for internal use by this library are named
        ``internal``.
