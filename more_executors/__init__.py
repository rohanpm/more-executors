"""A composable library of Python executors.

This library is intended for use with the
[`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html)
module.  It includes a collection of `Executor` implementations in order to
extend the behavior of `Future` objects.

Compatible with Python 2.6, 2.7 and 3.x.
"""

__all__ = ['retry']
