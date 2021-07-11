class CanBind(object):
    def bind(self, *args, **kwargs):
        from .executors import Executors

        return Executors.bind(self, *args, **kwargs)

    def flat_bind(self, *args, **kwargs):
        from .executors import Executors

        return Executors.flat_bind(self, *args, **kwargs)


class CanCustomize(object):
    def __propagate_name(self, kwargs):
        for name_attr in ("_name", "_CustomizableThreadPoolExecutor__name"):
            if hasattr(self, name_attr) and "name" not in kwargs:
                kwargs["name"] = getattr(self, name_attr)
                return

    def with_retry(self, *args, **kwargs):
        from .executors import Executors

        self.__propagate_name(kwargs)
        return Executors.with_retry(self, *args, **kwargs)

    def with_map(self, *args, **kwargs):
        from .executors import Executors

        self.__propagate_name(kwargs)
        return Executors.with_map(self, *args, **kwargs)

    def with_flat_map(self, *args, **kwargs):
        from .executors import Executors

        self.__propagate_name(kwargs)
        return Executors.with_flat_map(self, *args, **kwargs)

    def with_poll(self, *args, **kwargs):
        from .executors import Executors

        self.__propagate_name(kwargs)
        return Executors.with_poll(self, *args, **kwargs)

    def with_timeout(self, *args, **kwargs):
        from .executors import Executors

        self.__propagate_name(kwargs)
        return Executors.with_timeout(self, *args, **kwargs)

    def with_throttle(self, *args, **kwargs):
        from .executors import Executors

        self.__propagate_name(kwargs)
        return Executors.with_throttle(self, *args, **kwargs)

    def with_cancel_on_shutdown(self, *args, **kwargs):
        from .executors import Executors

        self.__propagate_name(kwargs)
        return Executors.with_cancel_on_shutdown(self, *args, **kwargs)

    def with_asyncio(self, *args, **kwargs):
        from .executors import Executors

        self.__propagate_name(kwargs)
        return Executors.with_asyncio(self, *args, **kwargs)


class CanCustomizeBind(CanBind, CanCustomize):
    pass
