from functools import update_wrapper


class BoundCallable(object):
    def __init__(self, executor, fn):
        self.__executor = executor
        self.__fn = fn
        update_wrapper(self, fn)

    def __call__(self, *args, **kwargs):
        return self.__executor.submit(self.__fn, *args, **kwargs)
