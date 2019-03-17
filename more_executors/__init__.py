"""A library of composable Python executors.

- [Documentation](https://rohanpm.github.io/more-executors/)
- [Source](https://github.com/rohanpm/more-executors)
- [PyPI](https://pypi.python.org/pypi/more-executors)

This library is intended for use with the
[`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html)
module.  It includes a collection of `Executor` implementations in order to
extend the behavior of `Future` objects.

Compatible with Python 2.6, 2.7 and 3.x.

This documentation was built from an unknown revision.
"""
from ._impl.executors import Executors

__all__ = ['Executors']
