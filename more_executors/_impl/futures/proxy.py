# -*- coding: utf-8 -*-

import math

from more_executors._impl.map import MapFuture
from more_executors._impl.common import MAX_TIMEOUT
from .check import ensure_future
from ..metrics import track_future


class ProxyFuture(MapFuture):
    # A future which proxies many calls through to the underlying object.
    def __init__(self, delegate, timeout):
        self.__timeout = timeout
        super(ProxyFuture, self).__init__(delegate)

    @property
    def __result(self):
        return self.result(self.__timeout)

    def __len__(self):
        return len(self.__result)

    def __getattr__(self, name):
        if name == "_ProxyFuture__result":
            # A rather wacky edge-case...
            # If self.__result is called, and the future has failed,
            # and the future's exception is an AttributeError:
            # python will interpret "AttributeError raised during self.__result"
            # as "I should try to use __getattr__ to get __result".
            # But we try to access self.__result again a few lines later
            # which would result in infinite recursion.
            # In that case, just raise the underlying exception (which we
            # know must be an AttributeError).
            raise self.exception()

        if name.startswith("__"):
            # Do not allow any special properties to trigger resolution
            # of the future, other than those we've explicitly proxied.
            raise AttributeError()

        return getattr(self.__result, name)

    def __getitem__(self, key):
        return self.__result[key]

    def __setitem__(self, key, value):
        self.__result[key] = value

    def __delitem__(self, key):
        del self.__result[key]

    def __iter__(self):
        return iter(self.__result)

    def __contains__(self, item):
        return item in self.__result

    def __add__(self, other):
        return self.__result + other

    def __sub__(self, other):
        return self.__result - other

    def __mul__(self, other):
        return self.__result * other

    def __div__(self, other):
        return self.__result.__div__(other)

    def __truediv__(self, other):
        return self.__result.__truediv__(other)

    def __floordiv__(self, other):
        return self.__result.__floordiv__(other)

    def __mod__(self, other):
        return self.__result % other

    def __divmod__(self, other):
        return divmod(self.__result, other)

    def __pow__(self, other, *modulo):
        return pow(self.__result, other, *modulo)

    def __lshift__(self, other):
        return self.__result << other

    def __rshift__(self, other):
        return self.__result >> other

    def __and__(self, other):
        return self.__result & other

    def __xor__(self, other):
        return self.__result ^ other

    def __or__(self, other):
        return self.__result | other

    def __neg__(self):
        return -self.__result  # pylint: disable=invalid-unary-operand-type

    def __pos__(self):
        return +self.__result  # pylint: disable=invalid-unary-operand-type

    def __abs__(self):
        return abs(self.__result)

    def __invert__(self):
        return ~self.__result  # pylint: disable=invalid-unary-operand-type

    def __complex__(self):
        return complex(self.__result)

    def __int__(self):
        return int(self.__result)

    def __float__(self):
        return float(self.__result)

    def __round__(self, *ndigits):
        return round(self.__result, *ndigits)

    def __trunc__(self):
        return self.__result.__trunc__()

    def __floor__(self):
        return math.floor(self.__result)

    def __ceil__(self):
        return math.ceil(self.__result)

    # Not proxied because I think it's more important for cases like this:
    #
    #  def some_fn(): Future|None
    #     ...
    #  f = some_fn()
    #  if f:
    #    # means some_fn returned a Future
    #  else:
    #    # means some_fn returned None
    #
    # ... to work as expected at first glance.
    #
    # Though not proxied, it has to be overridden (to return True for non-None)
    # because otherwise python checks if __len__() == 0.
    def __bool__(self):
        return True

    def __nonzero__(self):
        # python 2.x name for __bool__
        return self.__bool__()

    # Not proxied because nothing in Python itself uses it and I don't
    # want to spend the effort testing it
    # def __matmul__(self, other):

    # Not proxied because frankly I don't understand what this operator is
    # def __index__(self):

    # Not proxied because it seems unlikely anyone would implement a method
    # returning a future with a context manager.
    # def __enter__(self):
    # def __exit__(self, exc_type, exc_value, traceback):

    # String formatting functions and similar are not proxied as I'm
    # concerned about code like LOG.debug("Enqueued: %s", some_f) becoming
    # blocking only when the logger is enabled. Having major side-effects
    # on str() seems too risky.
    # def __str__(self):
    # def __bytes__(self):
    # def __format__(self, format_spec):

    # repr should never be proxied so that debugging code etc doesn't mislead
    # about the type of objects
    # def __repr__(self):

    # Not proxied so that:
    # - futures can be stored in dicts/lists which can be checked for membership
    #   without blocking
    # - no way to make it commutative?  e.g. we can make Future[123] == 123
    #   work but not 123 == Future[123].
    # def __eq__(self, other):

    # Not proxied so futures can be stored in dicts/sets without blocking
    # def __hash__(self):

    # Not proxied because eq is not proxied, which means expected relationship
    # between these operators can't be satisfied
    # def __ne__(self, other):
    # def __gt__(self, other):
    # def __ge__(self, other):
    # def __lt__(self, other):
    # def __le__(self, other):


@ensure_future
def f_proxy(f, **kwargs):
    """Proxy calls on a future through to the future's result.

    The value returned by this function is a future resolved with the
    same result (or exception) as the input future ``f``.  It will also
    proxy most attribute lookups and method calls through to the
    underlying result, awaiting the result when needed.

    Note that since the returned value is intended to remain usable as
    a ``Future``, this proxy is relatively conservative and avoids
    proxying functionality which would clash with the ``Future``
    interface.

    Functionality which is not proxied includes:

    - conversion to boolean (``__bool__``)
    - conversion to string (``__str__``, ``__repr__``)
    - methods relating to object identity (``__eq__``, ``__hash__``)

    Signature: :code:`Future<X> ⟶ Future<X>`

    Arguments:
        f (~concurrent.futures.Future)
            Any future.
        timeout (float)
            Timeout applied when awaiting the future's result
            during proxied calls.

    Returns:
        :class:`~concurrent.futures.Future`
            a Future which proxies calls through to the
            future's result as needed.

    .. versionadded:: 2.3.0
    """
    return track_future(
        ProxyFuture(f, timeout=kwargs.pop("timeout", MAX_TIMEOUT)), type="proxy"
    )
