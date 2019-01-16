Cancellation of futures: ``f_nocancel``, ``CancelOnShutdownExecutor``
=====================================================================

Futures API
-----------

.. automodule:: more_executors.futures
   :members: f_nocancel

Executors API
-------------

.. autoclass:: more_executors.cancel_on_shutdown.CancelOnShutdownExecutor
   :members:

.. automethod:: more_executors.Executors.with_cancel_on_shutdown(executor, logger=None)
