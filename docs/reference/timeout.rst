Timing out futures: ``f_timeout``, ``TimeoutExecutor``
======================================================

Futures API
-----------

.. automodule:: more_executors.futures
   :members: f_timeout

Executors API
-------------

.. autoclass:: more_executors.timeout.TimeoutExecutor
   :members: submit_timeout

.. automethod:: more_executors.Executors.with_timeout(executor, timeout, logger=None)
