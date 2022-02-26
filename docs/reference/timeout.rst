Timing out futures: ``f_timeout``, ``TimeoutExecutor``
======================================================

Futures API
-----------

.. autofunction:: more_executors.f_timeout


Executors API
-------------

.. autoclass:: more_executors.TimeoutExecutor
   :members: submit_timeout

.. automethod:: more_executors.Executors.with_timeout(executor, timeout, logger=None)
