Retrying: ``RetryExecutor``
===========================

RetryExecutor produces futures which will implicitly retry on error.

.. autoclass:: more_executors.RetryExecutor
   :members:

.. automethod:: more_executors.Executors.with_retry(executor, retry_policy=None, logger=None)

.. autoclass:: more_executors.RetryPolicy
   :members:

.. autoclass:: more_executors.ExceptionRetryPolicy(max_attempts, exponent, sleep, max_sleep, exception_base)
   :members:

