Transforming futures: ``f_map``, ``f_flat_map``, ``MapExecutor``, ``FlatMapExecutor``
=====================================================================================

The output value of a future can be mapped to other values using a
provided function.

Futures API
-----------

.. autofunction:: more_executors.f_map

.. autofunction:: more_executors.f_flat_map


Executors API
-------------

.. autoclass:: more_executors.MapExecutor
   :members: submit

.. automethod:: more_executors.Executors.with_map(executor, fn=None, error_fn=None, logger=None)


.. autoclass:: more_executors.FlatMapExecutor

.. automethod:: more_executors.Executors.with_flat_map(executor, fn=None, error_fn=None, logger=None)
