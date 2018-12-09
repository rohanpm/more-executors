"""Transform the output value of a future asynchronously."""

from more_executors.map import _MapFuture, MapExecutor

__pdoc__ = {}
__pdoc__['FlatMapExecutor.shutdown'] = None
__pdoc__['FlatMapExecutor.map'] = None
__pdoc__['FlatMapExecutor.submit'] = """Submit a callable.

The returned `Future` will have its output value transformed by the
map function passed to this executor.

- If the map function returns a `Future`, the result/exception of
  that future will be propagated to the future returned by this function.
- If the map function returns anything other than a `Future`, the returned
  future will fail with a `TypeError`.
- If the map function raises an exception, the returned future will fail
  with that exception.
"""


class _FlatMapFuture(_MapFuture):
    def __init__(self, *args, **kwargs):
        self.__flattened = False
        super(_FlatMapFuture, self).__init__(*args, **kwargs)

    def _on_mapped(self, result):
        if self.__flattened:
            return super(_FlatMapFuture, self)._on_mapped(result)

        # Result *must* be a future.
        # We'd crash in set_delegate if not.
        # Let's raise this more helpful exception prior to that.
        if not callable(getattr(result, 'add_done_callback', None)):
            raise TypeError(
                "FlatMapExecutor's function did not return a Future!\n"
                "  Function: %s\n"
                "  Returned: %s" % (repr(self._map_fn), repr(result)))

        self.__flattened = True
        self._map_fn = lambda x: x
        self._set_delegate(result)


class FlatMapExecutor(MapExecutor):
    """An `Executor` which delegates to another `Executor` while mapping
    output values through a given `Future`-producing function.

    This executor behaves like `MapExecutor`, except that the given mapping
    function must return instances of `Future`, and the mapped future is
    flattened into the future returned from this executor.
    This allows chaining multiple future-producing functions into a single
    future.

    *Since version 1.12.0*
    """

    _FUTURE_CLASS = _FlatMapFuture
