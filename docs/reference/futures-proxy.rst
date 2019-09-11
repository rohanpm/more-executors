Proxy futures: ``f_proxy``
==========================

The ``f_proxy`` function allows wrapping a future with a proxy which will
pass attribute lookups and method calls through to the underlying result,
blocking as needed.

The primary goal of ``f_proxy`` is to make it possible to define APIs
which support both blocking and non-blocking coding styles.

Example
-------

Imagine we have defined some classes as follows:

.. code-block:: python

    class DatabaseService:
        def get_connection(self):
            """Obtain a connection to this application's database.
            Returns a Future[DatabaseConnection]."""
            ...

    class DatabaseConnection:
        def query(self, sql, *params):
            """Perform an SQL query using this connection.
            Returns a Future[DatabaseCursor]."""
            ...

    class DatabaseCursor:
        def __iter__(self):
            """Iterate over all results referenced by this cursor."""
            ...

This API could be used with a non-blocking coding style by composing
futures:

.. code-block:: python

    def process_results(cursor):
        for row in cursor:
           # assume it does something useful with each row
           ...

    connection = db_service.get_connection()
    cursor = f_flat_map(connection, lambda c: c.query(some_sql))
    results = f_map(cursor, process_results)

Or it could be used in a blocking coding style by adding calls to
``.result()``:

.. code-block:: python

    connection = db_service.get_connection().result()
    cursor = connection.query(some_sql).result()
    results = process_results(cursor)

If we define the API as returning proxy futures (i.e. wrap each returned
future using ``f_proxy``), the above two code snippets will continue to
work, and the below example also becomes possible: using the API in a
blocking coding style without requiring explicit calls to ``.result()``:

.. code-block:: python

    connection = db_service.get_connection()
    cursor = connection.query(some_sql)
    results = process_results(cursor)

.. automodule:: more_executors.futures

    .. autofunction:: f_proxy(f, timeout=None)
