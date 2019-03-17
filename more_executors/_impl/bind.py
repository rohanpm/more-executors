from functools import update_wrapper

from .wrap import CanCustomize


class BoundCallable(CanCustomize, object):
    def __init__(self, executor, fn):
        self.__executor = executor
        self.__fn = fn

        try:
            update_wrapper(self, fn)
        except AttributeError:
            # Update wrapper if we can, but not fatal if we can't
            pass

    def __call__(self, *args, **kwargs):
        return self.__executor.submit(self.__fn, *args, **kwargs)
