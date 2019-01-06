Throttling: ``ThrottleExecutor``
================================

ThrottleExecutor limits the number of concurrently executing futures.

.. autoclass:: more_executors.throttle.ThrottleExecutor
   :members:

.. automethod:: more_executors.Executors.with_throttle(executor, count, logger=None)
