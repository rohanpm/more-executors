Boolean operations: ``f_or``, ``f_and``
=======================================

Provides ``AND`` and ``OR`` operations over futures.

Short circuit
-------------

Much like a standard boolean expression, these operations are short-circuited
where possible.

Futures which are no longer needed in order to calculate the output value will
be canceled. In cases where this is not appropriate, consider wrapping the
input(s) in :meth:`~more_executors.f_nocancel`.

Example
.......

Consider this Python statement:

.. code-block:: python

   result = x() or y() or z()

If ``x()`` returns a false value and ``y()`` returns a true value, the result
of the expression is the returned value of ``y()``, and ``z()`` is not
evaluated.

Now consider the equivalent with futures:

.. code-block:: python

   future = f_or(f_x, f_y, f_z)

All of ``f_x``, ``f_y`` and ``f_z`` may be running concurrently.
If ``f_y`` completes first with a true value, ``f_x`` and ``f_z``
may be cancelled.

If we wanted to allow ``f_z`` to continue running even if its output
value would not be used, we can instead write:

.. code-block:: python

   future = f_or(f_x, f_y, f_nocancel(f_z))


.. autofunction:: more_executors.f_or

.. autofunction:: more_executors.f_and

