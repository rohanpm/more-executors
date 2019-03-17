from .map import MapFuture, MapExecutor


class FlatMapFuture(MapFuture):
    def __init__(self, *args, **kwargs):
        self.__flattened = False
        super(FlatMapFuture, self).__init__(*args, **kwargs)

    def _on_mapped(self, result):
        if self.__flattened:
            return super(FlatMapFuture, self)._on_mapped(result)

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
    """An executor which delegates to another executor while mapping
    output values through a given future-producing function.

    This executor behaves like :class:`~more_executors.map.MapExecutor`,
    except that the given mapping function must return instances of
    :class:`~concurrent.futures.Future`, and the mapped future is
    flattened into the future returned from this executor.
    This allows chaining multiple future-producing functions into a single
    future.

    - If the map function returns a :class:`~concurrent.futures.Future`, the
      result/exception of that future will be propagated to the future returned
      by this executor.
    - If the map function returns any other type, the returned future will fail
      with a :class:`TypeError`.
    - If the map function raises an exception, the returned future will fail
      with that exception.

    .. versionadded: 1.12.0
    """

    _FUTURE_CLASS = FlatMapFuture
