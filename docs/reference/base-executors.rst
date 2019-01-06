Base executors: ``thread_pool``, ``process_pool``, ``sync``
===========================================================

concurrent.futures
..................

A few convenience methods are provided for the creation of
:mod:`concurrent.futures` executors. The executors produced by these methods
include the :class:`more_executors.Executors` `with_*` methods for
:ref:`composing executors`.

.. automethod:: more_executors.Executors.thread_pool
.. automethod:: more_executors.Executors.process_pool

Sync
....

SyncExecutor is a base executor which invokes any submitted callables
immediately in the calling thread.

.. autoclass:: more_executors.sync.SyncExecutor
   :members:

.. automethod:: more_executors.Executors.sync(logger=None)
