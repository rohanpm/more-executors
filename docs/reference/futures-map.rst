Transforming futures: ``f_map``, ``f_flat_map``, ``MapExecutor``, ``FlatMapExecutor``
=====================================================================================

The output value of a future can be mapped to other values using a
provided function.

Futures API
-----------

.. automodule:: more_executors.futures
   :members: f_map, f_flat_map

Executors API
-------------

.. autoclass:: more_executors.map.MapExecutor
   :members: submit

.. automethod:: more_executors.Executors.with_map(executor, fn=None, error_fn=None, logger=None)


.. autoclass:: more_executors.flat_map.FlatMapExecutor

.. automethod:: more_executors.Executors.with_flat_map(executor, fn=None, error_fn=None, logger=None)
