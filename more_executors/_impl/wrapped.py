from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from .wrap import CanCustomizeBind


class CustomizableThreadPoolExecutor(CanCustomizeBind, ThreadPoolExecutor):
    pass


class CustomizableProcessPoolExecutor(CanCustomizeBind, ProcessPoolExecutor):
    pass
