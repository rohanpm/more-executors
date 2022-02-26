Cancellation of futures: ``f_nocancel``, ``CancelOnShutdownExecutor``
=====================================================================

Futures API
-----------

.. autofunction:: more_executors.f_nocancel

Executors API
-------------

.. autoclass:: more_executors.CancelOnShutdownExecutor
   :members:

.. automethod:: more_executors.Executors.with_cancel_on_shutdown(executor, logger=None)
