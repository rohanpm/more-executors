Retrying: ``RetryExecutor``
===========================

RetryExecutor produces futures which will implicitly retry on error.

.. autoclass:: more_executors.retry.RetryExecutor
   :members:

.. automethod:: more_executors.Executors.with_retry(executor, retry_policy=None, logger=None)

.. autoclass:: more_executors.retry.RetryPolicy
   :members:

.. autoclass:: more_executors.retry.ExceptionRetryPolicy(max_attempts, exponent, sleep, max_sleep, exception_base)
   :members:

