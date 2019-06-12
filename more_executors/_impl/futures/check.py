from functools import wraps


def ensure_futures(f):
    @wraps(f)
    def new_fn(*args, **kwargs):
        to_check = list(args)
        to_check.extend(kwargs.values())

        for arg in to_check:
            if not is_future(arg):
                raise TypeError(
                    "%s() called with non-future value: %s" % (f.__name__, repr(arg))
                )

        return f(*args, **kwargs)

    return new_fn


def ensure_future(f):
    @wraps(f)
    def new_fn(*args, **kwargs):
        arg = None
        if args:
            arg = args[0]
        else:
            arg = kwargs.get("future")

        if not is_future(arg):
            raise TypeError(
                "%s() called with non-future value: %s" % (f.__name__, repr(arg))
            )

        return f(*args, **kwargs)

    return new_fn


def is_future(f):
    return "add_done_callback" in dir(f)
