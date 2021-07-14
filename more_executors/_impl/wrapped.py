import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from .wrap import CanCustomizeBind
from .metrics import metrics, track_future
from .helpers import ShutdownHelper


class CustomizableThreadPoolExecutor(CanCustomizeBind, ThreadPoolExecutor):
    def __init__(self, *args, **kwargs):
        self.__name = kwargs.pop("name", "default")
        self.__shutdown = ShutdownHelper()

        if (
            sys.version_info >= (3, 6)
            and len(args) < 2
            and "thread_name_prefix" not in kwargs
            and self.__name != "default"
        ):
            kwargs["thread_name_prefix"] = "ThreadPoolExecutor-%s" % self.__name

        super(CustomizableThreadPoolExecutor, self).__init__(*args, **kwargs)
        metrics.EXEC_TOTAL.labels(type="threadpool", executor=self.__name).inc()
        metrics.EXEC_INPROGRESS.labels(type="threadpool", executor=self.__name).inc()

    def shutdown(self, *args, **kwargs):
        if self.__shutdown():
            metrics.EXEC_INPROGRESS.labels(
                type="threadpool", executor=self.__name
            ).dec()
            super(CustomizableThreadPoolExecutor, self).shutdown(*args, **kwargs)

    def submit(self, *args, **kwargs):
        with self.__shutdown.ensure_alive():
            f = super(CustomizableThreadPoolExecutor, self).submit(*args, **kwargs)
            track_future(f, type="threadpool", executor=self.__name)
            return f


class CustomizableProcessPoolExecutor(CanCustomizeBind, ProcessPoolExecutor):
    def __init__(self, *args, **kwargs):
        kwargs.pop("name", None)
        super(CustomizableProcessPoolExecutor, self).__init__(*args, **kwargs)
