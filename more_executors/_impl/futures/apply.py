# -*- coding: utf-8 -*-

from .base import wrap


# for wrapping arguments.
# This value means an argument came from *args rather than **kwargs
ARGS = object()


def f_apply(future_fn, *future_args, **future_kwargs):
    """Call a function, where the function, its arguments and return value
    are all provided by futures.

    Signature: :code:`Future<fn<A[,B[,...]]⟶R>>, Future<A>[, Future<B>[, ...]] ⟶ Future<R>`

    Arguments:
        future_fn (:class:`~concurrent.futures.Future` of :class:`callable`)
            A future returning a function to be applied.
        future_args (~concurrent.futures.Future)
            Futures holding positional arguments for the function.
        future_kwargs (~concurrent.futures.Future)
            Futures holding keyword arguments for the function.

    Returns:
        ~concurrent.futures.Future:
            A future holding the returned value of the applied function.

    .. versionadded:: 1.19.0
    """
    wrapped_args = _wrap_args(*future_args, **future_kwargs)
    return _wrapped_f_apply(future_fn, wrapped_args)


def _wrap_args(*future_args, **future_kwargs):
    out = list()
    for arg in future_args:
        out.append((ARGS, arg))
    for key, value in future_kwargs.items():
        out.append((key, value))
    return out


def _wrapped_f_apply(future_fn, future_args):
    if not future_args:
        return wrap(future_fn).with_map(lambda fn: fn())()

    future_key_and_x = future_args[0]
    (key, future_x) = future_key_and_x
    future_args = future_args[1:]

    # future_fn takes multiple arguments.
    # Create a new equivalent future function which takes one less arg
    def fn_runner(fn, x):
        def out(*args, **kwargs):
            args = list(args)
            kwargs = kwargs.copy()
            if key is ARGS:
                args.insert(0, x)
            else:
                kwargs[key] = x
            return fn(*args, **kwargs)
        return out

    next_future_fn = wrap(future_x).with_flat_map(
        lambda x: wrap(future_fn).with_map(lambda fn: fn_runner(fn, x))()
    )()

    return _wrapped_f_apply(next_future_fn, future_args)
