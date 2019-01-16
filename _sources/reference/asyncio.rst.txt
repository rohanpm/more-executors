asyncio bridge: ``AsyncioExecutor``
===================================

AsyncioExecutor transforms :mod:`concurrent.futures` futures into
:mod:`asyncio` futures.

.. autoclass:: more_executors.asyncio.AsyncioExecutor

.. automethod:: more_executors.Executors.with_asyncio(executor, loop=None, logger=None)

