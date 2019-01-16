Binding callables to executors: ``bind``, ``flat_bind``
=======================================================

The :meth:`~more_executors.Executors.bind` method produces a callable which is
bound to a specific executor.

This is illustrated by the following example.
Consider this code to fetch data from a list of URLs expected to provide JSON,
with up to 8 concurrent requests and retries on failure, without using
:meth:`bind`:

.. code-block:: python

    executor = Executors.thread_pool(max_workers=8). \
        with_map(lambda response: response.json()). \
        with_retry()

    futures = [executor.submit(requests.get, url)
                for url in urls]

The following code using :meth:`bind` is functionally
equivalent:

.. code-block:: python

    async_get = Executors.thread_pool(max_workers=8). \
        bind(requests.get). \
        with_map(lambda response: response.json()). \
        with_retry()

    futures = [async_get(url) for url in urls]

The latter example using :meth:`bind` is more readable because the order of
the calls to set up the pipeline more closely reflects the order in
which the pipeline executes at runtime.

In contrast, without using :meth:`bind`, the *first* step of the pipeline -
:meth:`requests.get` - appears at the *end* of the code, which is harder
to follow.

:meth:`~more_executors.Executors.flat_bind` is also provided for use with
callables returning a future. It behaves in the same way as :meth:`bind`,
but avoids returning a nested future.

.. automethod:: more_executors.Executors.bind

.. automethod:: more_executors.Executors.flat_bind
